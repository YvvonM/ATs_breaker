import json 
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4
from sqlalchemy import delete, func, select, update
from sqlmodel import Session
from infrastructure.db.sync_engine import sync_session
from infrastructure.db.schema import (
    LLMCallRecordRow,
    LLMResponseCache,
    RevisionRecordRow,
)
logger = logging.getLogger(__name__)

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def get_cache_response(cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        with sync_session as session:
            row = session.get(LLMResponseCache, cache_key)
            if row is None:
                return None 

            return {
                "response_json": row.response_json,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
            }
    except Exception:
        logger.exception("Cache GET failed for key=%s", cache_key)
        return None

def put_cached_response(
    *,
    cache_key: str,
    prompt_version: str,
    agent: str,
    role: str,
    model: str,
    temperature: float,
    prompt_hash: str,
    response_json: str,
    input_tokens: int,
    output_tokens: int,
)-> bool:
    try:
        with sync_session() as session:
            existing = session.get(LLMResponseCache, cache_key)
            if existing is not None:
                return True

            row = LLMResponseCache(
                cache_key=cache_key,
                prompt_version=prompt_version,
                agent=agent,
                role=role,
                model=model,
                temperature=temperature,
                prompt_hash=prompt_hash,
                response_json=response_json,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                hit_count=0,
                last_hit_at=None,
                created_at=_utcnow(),
            )
            session.add(row)
            return True

    except Exception:
        logger.exception("Cache PUT failed for key=%s", cache_key)
        return False

def increment_cache_hit(cache_key: str) -> None:
    try:
        with sync_session() as session:
            session.execute(
                update(LLMResponseCache)
                .where(LLMResponseCache.cache_key == cache_key)
                .values(
                    hit_count=LLMResponseCache.hit_count + 1,
                    last_hit_at=_utcnow(),
                )
            )

    except Exception:
        logger.exception("Cache hit bump failed for key=%s", cache_key)

def purge_prompt_version(prompt_version: str) -> int:
    try:
        with sync_session() as session:
            result = session.execute(
                delete(LLMResponseCache).where(
                    LLMResponseCache.prompt_version == prompt_version
                )
            )
            return result.rowcount or 0
    except Exception:
        logger.exception("Cache purge failed for version=%s", prompt_version)
        return 0


def insert_llm_call_record(
    *,
    run_id: str,
    agent: str,
    role: str,
    model: str,
    temperature: float,
    prompt_hash: str,
    response_hash: str,
    cached: bool,
    input_tokens: int,
    output_tokens: int,
    latency_seconds: float,
    started_at: datetime,
    completed_at: datetime,
    error: Optional[str] = None,
) -> bool:
    """Insert one audit row per LLM call. Best-effort."""
    try:
        with sync_session() as session:
            row = LLMCallRecordRow(
                id=uuid4(),
                run_id=run_id,
                agent=agent,
                role=role,
                model=model,
                temperature=temperature,
                prompt_hash=prompt_hash,
                response_hash=response_hash,
                cached=cached,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_seconds=latency_seconds,
                started_at=started_at,
                completed_at=completed_at,
                error=error,
            )
            session.add(row)
        return True
    except Exception:
        logger.exception(
            "Failed to insert LLMCallRecordRow run=%s agent=%s role=%s",
            run_id,
            agent,
            role,
        )
        return False


def insert_revision_record(
    *,
    run_id: str,
    agent: str,
    iteration: int,
    status: str,
    output: Dict[str, Any],
    scores: Optional[Dict[str, float]] = None,
    feedback: Optional[Dict[str, List[str]]] = None,
    revision_notes: Optional[List[str]] = None,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    error: Optional[str] = None,
) -> bool:
    try:
        with sync_session() as session:
            row = RevisionRecordRow(
                id=uuid4(),
                run_id=run_id,
                agent=agent,
                iteration=iteration,
                status=status,
                output_json=json.dumps(output, default=_json_default),
                scores_json=(
                    json.dumps(scores, default=_json_default)
                    if scores is not None
                    else None
                    ),
                feedback_json=(
                    json.dumps(feedback, default=_json_default)
                    if feedback is not None
                    else None
                ),
                revision_notes_json=(
                    json.dumps(revision_notes, default=_json_default)
                    if revision_notes is not None
                    else None
                ),
                started_at=started_at,
                completed_at=completed_at,
                error=error,
            )
            session.add(row)
        return True
    except Exception:
        logger.exception(
            "Failed to insert RevisionRecordRow run=%s agent=%s iter=%s",
            run_id,
            agent,
            iteration,
        )

def get_run_token_usage(run_id: str) -> Dict[str, int]:
    """Sum tokens across all LLM calls for a run.

    Returns a dict with input_tokens, output_tokens, total, cached_calls,
    and total_calls. All zeros if the run has no calls yet.
    """
    empty = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total": 0,
        "cached_calls": 0,
        "total_calls": 0,
    }
    try:
        with sync_session() as session:
            total_calls = session.execute(
                select(func.count(LLMCallRecordRow.id)).where(
                    LLMCallRecordRow.run_id == run_id
                )
            ).scalar_one()

            cached_calls = session.execute(
                select(func.count(LLMCallRecordRow.id))
                .where(LLMCallRecordRow.run_id == run_id)
                .where(LLMCallRecordRow.cached.is_(True))
            ).scalar_one()
            input_sum = session.execute(
                select(func.coalesce(func.sum(LLMCallRecordRow.input_tokens), 0))
                .where(LLMCallRecordRow.run_id == run_id)
            ).scalar_one()

            output_sum = session.execute(
                select(func.coalesce(func.sum(LLMCallRecordRow.output_tokens), 0))
                .where(LLMCallRecordRow.run_id == run_id)
            ).scalar_one()
            return {
                "input_tokens": int(input_sum or 0),
                "output_tokens": int(output_sum or 0),
                "total": int((input_sum or 0) + (output_sum or 0)),
                "cached_calls": int(cached_calls or 0),
                "total_calls": int(total_calls or 0),
            }
    except Exception:
        logger.exception("get_run_token_usage failed for run=%s", run_id)
        return empty


def get_run_cache_hit_rate(run_id: str) -> float:
    """Fraction of LLM calls for a run that were served from cache (0.0-1.0)."""
    stats = get_run_token_usage(run_id)
    if stats["total_calls"] == 0:
        return 0.0
    return stats["cached_calls"] / stats["total_calls"]


def _json_default(obj: Any) -> Any:
    """JSON serializer fallback for objects json.dumps doesn't know."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):        
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):              
        return obj.dict()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

