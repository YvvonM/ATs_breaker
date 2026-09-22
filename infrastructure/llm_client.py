from __future__ import annotations 
import hashlib
import json
import logging 
import random 
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List,Dict, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from infrastructure.db import repository
from infrastructure.redis_service import redis_service

logger = logging.getLogger(__name__)
@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CallResult:
    response: Optional[Dict[str, Any]]
    usage: TokenUsage = field(default_factory=TokenUsage)
    cached: bool = False
    error: Optional[str] = None
    latency_seconds: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    prompt_hash: str = ""

def call_llm(
    *,
    chain: Any,
    prompt_inputs: Dict[str, Any],
    run_id: str,
    agent: str,
    role: str,
    prompt_version: str,
    model: str,
    temperature: float,
    max_attempts: int = 3,
) -> CallResult:
    started_at = _utcnow()

    
    prompt_hash = _hash_prompt(prompt_inputs)
    cache_key = _cache_key(
        prompt_version=prompt_version,
        agent=agent,
        role=role,
        model=model,
        temperature=temperature,
        prompt_hash=prompt_hash,
    )
    cached = repository.get_cached_response(cache_key)
    if cached is not None:
        try:
            response = json.loads(cached["response_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Cached response was not valid JSON, ignoring: %s", e)
            response = None

        if response is not None:

            repository.increment_cache_hit(cache_key)
            completed_at = _utcnow()
            usage = TokenUsage(
                    input_tokens=cached["input_tokens"],
                    output_tokens=cached["output_tokens"],
            )
            latency = (completed_at - started_at).total_seconds()

            _emit_event(
                        run_id,
                        "llm_call",
                        {
                            "agent": agent,
                            "role": role,
                            "cached": True,
                            "tokens": usage.total,
                        },
                    )

            _audit(
                run_id=run_id,
                agent=agent,
                role=role,
                model=model,
                temperature=temperature,
                prompt_hash=prompt_hash,
                response_hash=_hash_json(response),
                cached=True,
                usage=usage,
                latency_seconds=latency,
                started_at=started_at,
                completed_at=completed_at,
                error=None,
            )

            return CallResult(
                response=response,
                usage=usage,
                cached=True,
                latency_seconds=latency,
                started_at=started_at,
                completed_at=completed_at,
                prompt_hash=prompt_hash,
            )

    response, usage, error, completed_at = _invoke_with_retry(
        chain=chain,
        prompt_inputs=prompt_inputs,
        max_attempts=max_attempts,
    )
    latency = (completed_at - started_at).total_seconds()

    if response is not None and error is None:
        repository.put_cached_response(
            cache_key=cache_key,
            prompt_version=prompt_version,
            agent=agent,
            role=role,
            model=model,
            temperature=temperature,
            prompt_hash=prompt_hash,
            response_json=json.dumps(response),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,)


    _emit_event(
        run_id,
        "llm_call",
        {
            "agent": agent,
            "role": role,
            "cached": False,
            "tokens": usage.total,
            "error": error,
        },
    )
    _audit(
        run_id=run_id,
        agent=agent,
        role=role,
        model=model,
        temperature=temperature,
        prompt_hash=prompt_hash,
        response_hash=_hash_json(response) if response is not None else "",
        cached=False,
        usage=usage,
        latency_seconds=latency,
        started_at=started_at,
        completed_at=completed_at,
        error=error,
    )
    return CallResult(
        response=response,
        usage=usage,
        cached=False,
        error=error,
        latency_seconds=latency,
        started_at=started_at,
        completed_at=completed_at,
        prompt_hash=prompt_hash,
    )

def _invoke_with_retry(
    *,
    chain: Any,
    prompt_inputs: Dict[str, Any],
    max_attempts: int,
) -> tuple[Optional[Dict[str, Any]], TokenUsage, Optional[str], datetime]:
    usage = TokenUsage()
    last_error: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            raw = chain.invoke(prompt_inputs)
            response, usage = _extract_response_and_usage(raw)
            if response is None:
                return None, usage, "Structured output parsing returned no response.", _utcnow()
            return response, usage, None, _utcnow()
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            transient = _is_transient_error(e)
            logger.warning(
                "LLM call failed (attempt %d/%d, transient=%s): %s",
                attempt,
                max_attempts,
                transient,
                last_error,
            )

            if not transient or attempt == max_attempts:
                break
            _sleep_with_jitter(attempt)

    return None, usage, last_error, _utcnow()

def _is_transient_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    if "ratelimit" in name or "rate_limit" in msg or "429" in msg:
        return True
    if any(code in msg for code in ("500", "502", "503", "504")):
        return True
    if any(k in name for k in ("timeout", "connection", "network")):
        return True
    if any(k in msg for k in ("timeout", "connection reset", "broken pipe")):
        return True

    return False

def _sleep_with_jitter(attempt: int) -> None:
    base = 2 ** (attempt - 1)
    jitter = random.uniform(0, 0.5)
    time.sleep(base + jitter)

def _extract_response_and_usage(
    raw: Any,
) -> tuple[Optional[Dict[str, Any]], TokenUsage]:
    if isinstance(raw, dict) and "raw" in raw and "parsed" in raw:
        raw_msg = raw.get("raw")
        usage_meta = getattr(raw_msg, "usage_metadata", None) or {}
        usage = TokenUsage(
            input_tokens=int(usage_meta.get("input_tokens", 0) or 0),
            output_tokens=int(usage_meta.get("output_tokens", 0) or 0),
        )
        parsed = raw.get("parsed")
        if parsed is None:
            err = raw.get("parsing_error")
            logger.warning("Structured output parsing failed: %s", err)
            return None, usage
        if hasattr(parsed, "model_dump"):
            parsed = parsed.model_dump(mode="json")
        if isinstance(parsed, dict):
            return parsed, usage
        logger.warning("Structured output 'parsed' was not a dict/model: %r", type(parsed))
        return None, usage

    if isinstance(raw, dict):
        return raw, TokenUsage()

    usage_meta = getattr(raw, "usage_metadata", None) or {}
    usage = TokenUsage(
        input_tokens=int(usage_meta.get("input_tokens", 0) or 0),
        output_tokens=int(usage_meta.get("output_tokens", 0) or 0),
    )
    content = getattr(raw, "content", None)
    if isinstance(content, str):
        try:
            return json.loads(content), usage
        except json.JSONDecodeError:
            logger.warning("LLM content was not valid JSON")
            return None, usage
    if isinstance(content, dict):
        return content, usage
    return None, usage

def _hash_prompt(prompt_inputs: Dict[str, Any]) -> str:
    canonical = json.dumps(prompt_inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_json(obj: Optional[Dict[str, Any]]) -> str:
    if obj is None:
        return ""
    canonical = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _cache_key(
    *,
    prompt_version: str,
    agent: str,
    role: str,
    model: str,
    temperature: float,
    prompt_hash: str,
) -> str:
    raw = "|".join([
        prompt_version,
        agent,
        role,
        model,
        f"{temperature:.4f}",
        prompt_hash,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _audit(
    *,
    run_id: str,
    agent: str,
    role: str,
    model: str,
    temperature: float,
    prompt_hash: str,
    response_hash: str,
    cached: bool,
    usage: TokenUsage,
    latency_seconds: float,
    started_at: datetime,
    completed_at: datetime,
    error: Optional[str],
) -> None:
    try:
        repository.insert_llm_call_record(
            run_id=run_id,
            agent=agent,
            role=role,
            model=model,
            temperature=temperature,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            cached=cached,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_seconds=latency_seconds,
            started_at=started_at,
            completed_at=completed_at,
            error=error,
        )
    except Exception:
        logger.exception("Failed to insert LLMCallRecordRow")

def _emit_event(run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    try:
        redis_service.emit_event(run_id, event_type, payload)
    except Exception:
        logger.exception("Failed to emit Redis event %s", event_type)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
        