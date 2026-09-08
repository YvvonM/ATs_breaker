import json 
import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Any, Dict, Optional, List
from langchain_groq import ChatGroq
import hashlib
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from .config import MODEL, BASE_URL
from dotenv import load_dotenv
from datetime import datetime
from .prompts import _KEYWORD_SYSTEM_PROMPT, _KEYWORD_HUMAN_PROMPT
from agents.resume_rewriting.dtos.keyword_dto import (KeywordAgentOutput,
    KeywordContent,
    KeywordStructured,
    KeywordSentence as DTOSentence)
from agents.resume_rewriting.dtos.base import AgentMetadata
from infrastructure.redis_service import redis_service
from infrastructure.redis_client import redis_client
load_dotenv()

_KEYWORD_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _KEYWORD_SYSTEM_PROMPT),
    ("human", _KEYWORD_HUMAN_PROMPT),
])

class KeywordExtractor:
    def __init__(self, model: str = MODEL, api_key: str = None):
        self.model = model
        self._llm = ChatGroq(
            model=self.model,
            api_key=api_key or os.getenv("GROQ_API_KEY"),
            temperature=0.0,
        )
        self._chain = _KEYWORD_PROMPT|self._llm|JsonOutputParser()
        self._redis = redis_service

    def _get_cache_key(self, job_description: str) -> str:
        """Generate a cache key based on the job description."""
        hash_object = hashlib.sha256(job_description.encode())
        return f"keyword_extraction:{hash_object.hexdigest()}"

    def _cache_result(self, cache_key: str, dto: KeywordAgentOutput) -> None:
        """Cache the result in Redis."""
        try:
            data = {
                'flat_keywords': dto.content.keywords,
                "keyword_sentences": [
                    {"sentence": s.sentence, "keywords": s.keywords}
                    for s in dto.content.keyword_sentences
                ],
                "keyword_count": dto.structured.keyword_count,
                "sentence_count": dto.structured.sentence_count,
                "model_used": dto.metadata.model_used,
                "execution_time":dto.metadata.execution_time,
                "token_count": dto.metadata.token_count,
                "timestamp": datetime.now().isoformat()
                
            }
            self._redis.store_job_data("cache", cache_key, data, ttl=604800)
            print(f"Cached extraction result: {cache_key}")

        except Exception as e:
            print(f"Error caching result: {str(e)}")

    def _get_cached_dto(self, cache_key: str) -> Optional[KeywordAgentOutput]:
        try:
            data = self._redis.get_job_data("cache", cache_key)
            if data:
                print(f"Cache hit: {cache_key}")
                return KeywordAgentOutput(
                    content= KeywordContent(
                        keywords = data.get("flat_keywords",[]),
                        keyword_sentences= [DTOSentence(
                            sentence = entry.get("sentence", ''),
                            keyword = entry.get("keywords", []))
                        for entry in data.get("keyword_sentences")]

                    ),
                    structured= KeywordStructured(
                        flat_keywords=data.get("flat_keywords", []),
                        keyword_count=data.get("keyword_count", 0),
                        sentence_count=data.get("sentence_count", 0)
                    ),
                    metadata = AgentMetadata(
                        model_used=data.get("model_used", self.model),
                        execution_time=data.get("execution_time", 0),
                        token_count=data.get("token_count", 0),
                        status="completed",
                        started_at=datetime.now(),
                        completed_at=datetime.now()
                    ),
                    error = None
                )
                
        except Exception as e:
            print(f"Error retrieving cached result: {str(e)}")
            return None

    def extract(self, job_description: str, run_id: Optional[str] = None, use_cache: bool = True) -> KeywordAgentOutput:
        start_time = datetime.now()
        if not job_description or not job_description.strip():
            return KeywordAgentOutput(
                content = KeywordContent(keywords=[], keyword_sentences=[]),
                structured= KeywordStructured(
                    flat_keywords=[],
                    keyword_count=0,
                    sentence_count=0
                ),
                metadata=AgentMetadata(
                    model_used=self.model,
                    execution_time=0,
                    token_count=0,
                    status="failed",
                    started_at=start_time,
                    completed_at=datetime.now()
                ),
                error = "Job description is empty or invalid."
            )

        cache_key = self._get_cache_key(job_description)
        if use_cache:
            cached_result = self._get_cached_dto(cache_key)
            if cached_result:
                return cached_result

        if run_id is None:
            run_id = self._redis.get_run_id()

        self._redis.set_job_status(run_id, "processing", "Keyword extraction started")

        try:
            parsed = self._chain.invoke({"job_description": job_description})
            raw_sentences = parsed.get("keyword_sentences", [])
            sentences = [
                DTOSentence(
                    sentence=entry.get("sentence", ""),
                    keywords=entry.get("keywords", [])
                )
                for entry in raw_sentences
                if entry.get('sentence')
            ]
            flat_keywords = []
            seen = set()
            for s in sentences:
                for kw in s.keywords:
                    key = kw.lower().strip()
                    if key and key not in seen:
                        seen.add(key)
                        flat_keywords.append(kw)

            dto = KeywordAgentOutput(
                content = KeywordContent(
                    keywords= flat_keywords,
                    keyword_sentences= sentences
                ),
                structured= KeywordStructured(
                    flat_keywords= flat_keywords,
                    keyword_count= len(flat_keywords),
                    sentence_count= len(sentences)
                ),
                metadata = AgentMetadata(
                    model_used=self.model,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    token_count=0,  # TODO: Get from LLM
                    status="completed",
                    started_at=start_time,
                    completed_at=datetime.now()
                ),
                error = None
            )
            print(f"Extracted {len(flat_keywords)} keywords from {len(sentences)} sentences")
            return dto
        except Exception as e:
            error_msg = f"Error during keyword extraction: {str(e)}"
            self._redis.set_job_status(run_id, "failed", error_msg)
            return KeywordAgentOutput(
               content=KeywordContent(keywords=[], keyword_sentences=[]),
               structured=KeywordStructured(
                   flat_keywords=[],
                    keyword_count=0,
                    sentence_count=0
               ),
               metadata=AgentMetadata(
                    model_used=self.model,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    token_count=0,
                    status="failed",
                    started_at=start_time,
                    completed_at=datetime.now()
                ),
                error = error_msg
            )

    def _store_dto(self, run_id: str, dto: KeywordAgentOutput) -> None:
        """Store DTO in Redis."""
        self._redis.store_job_data(run_id, "keyword_agent_output", dto.model_dump())
        self._redis.store_keywords(run_id, dto.content.keywords)
        self._redis.store_job_data(run_id, "keyword_count", dto.structured.keyword_count)
        self._redis.set_job_status(
            run_id,
            "completed",
            f"Extracted {dto.structured.keyword_count} keywords from {dto.structured.sentence_count} sentences"
        )
  
    def flat_keywords(self, result: KeywordAgentOutput) -> List[str]:
        """Flatten the keywords from the extraction result into a single list."""
        seen = set()
        flat: List[str] = []
        for entry in result.keyword_sentences:
            for kw in entry.keywords:
                key = kw.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    flat.append(kw)

        return flat


    def get_cached_flat_keywords(self, job_description: str) -> Optional[List[str]]:
        cache_key = self._get_cache_key(job_description)
        cached = self._get_cached_dto(cache_key)
        if cached:
            return self.flat_keywords(cached)
        return None


    def clear_cache(self, job_description: str) -> bool:
        """Clear cached result."""
        cache_key = self._get_cache_key(job_description)
        try:
            pattern = f"resume:cache:{cache_key}"
            keys = list(self._redis.client.scan_iter(match=pattern))
            if keys:
                self._redis.client.delete(*keys)
                return True
        except Exception as e:
            print(f"Cache clear failed: {e}")
        return False

    def extract_keywords(job_description: str,run_id: Optional[str] = None,use_cache: bool = True) -> KeywordAgentOutput:
        """Convenience function to extract keywords and get DTO."""
        extractor = KeywordExtractor()
        return extractor.extract(job_description, run_id, use_cache)

    