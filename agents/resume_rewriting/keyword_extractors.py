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
from .schemas import KeywordExtractionResult, KeywordSentence
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

    def _cache_result(self, cache_key: str, result: KeywordExtractionResult) -> None:
        """Cache the result in Redis."""
        try:
            data = {
                "keyword_sentences": [
                    {
                        "sentence": entry.sentence,
                        "keywords": entry.keywords
                    } for entry in result.keyword_sentences
                ],
                "extraction_notes": result.extraction_notes,
                "model_used": result.model_used,
                "timestamp": datetime.now().isoformat(),
                "keyword_count": len(result.keyword_sentences)
            }
            self._redis.store_job_data("cache", cache_key, data, ttl=604800)
            print(f"Cached extraction result: {cache_key}")

        except Exception as e:
            print(f"Error caching result: {str(e)}")

    def _get_cached_result(self, cache_key: str) -> Optional[KeywordExtractionResult]:
        try:
            data = self._redis.get_job_data("cache", cache_key)
            if data:
                print(f"Cache hit: {cache_key}")
                keyword_sentences = [
                    KeywordSentence(
                        sentence=entry.get("sentence", ""),
                        keywords=entry.get("keywords", [])
                    ) for entry in data.get("keyword_sentences", [])
                ]
                return KeywordExtractionResult(
                    keyword_sentences=keyword_sentences,
                    extraction_notes=f"Cached from {data.get('timestamp', 'unknown')}",
                    model_used=data.get("model_used", self.model)
                )
        except Exception as e:
            print(f"Error retrieving cached result: {str(e)}")
            return None

    def extract(self, job_description: str, run_id: Optional[str] = None, use_cache: bool = True) -> KeywordExtractionResult:
        if not job_description or not job_description.strip():
            return KeywordExtractionResult(keywords=[], 
                                           extraction_notes = "Job description is empty or invalid.", 
                                           model_used = self.model)

        cache_key = self._get_cache_key(job_description)
        if use_cache:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result

        if run_id is None:
            run_id = self._redis.get_run_id()

        self._redis.set_job_status(run_id, "processing", "Keyword extraction started")

        try:
            parsed = self._chain.invoke({"job_description": job_description})

        except Exception as e:
            return KeywordExtractionResult(keyword_sentences=[], 
                                           extraction_notes = f"Error during keyword extraction: {str(e)}", 
                                           model_used = self.model)

        raw_sentences = parsed.get("keyword_sentences", [])
        sentences =[
            KeywordSentence(
                sentence=entry.get("sentence", ""),
                keywords=entry.get("keywords", [])
            ) for entry in raw_sentences
            if entry.get("sentence")
        ]

        result = KeywordExtractionResult(
            keyword_sentences=sentences,
            extraction_notes="Keyword extraction completed successfully.",
            model_used=self.model
        )
        self._store_extraction_result(run_id, result, cache_key, job_description)


        return result   

    def _store_extraction_result(self, run_id: str, result: KeywordExtractionResult, 
                                 cache_key: str, job_description: str) -> None:
        self._redis.store_job_data(run_id, "extraction_result", {
            "keyword_sentences": [
                {"sentence": e.sentence, "keywords": e.keywords}
                for e in result.keyword_sentences
            ],
            "model_used": result.model_used,
            "extraction_notes": result.extraction_notes,
            "job_description_preview": job_description[:500]  
        })

        flat_keywords = self.flat_keywords(result)
        self._redis.store_keywords(run_id, flat_keywords)
        self._redis.store_job_data(run_id, "keyword_count", len(flat_keywords))
        self._redis.set_job_status(
            run_id, 
            "completed", 
            f"Extracted {len(flat_keywords)} keywords from {len(result.keyword_sentences)} sentences"
        )
        print(f"Stored extraction results for {run_id}")
        print(f"Found {len(flat_keywords)} unique keywords in {len(result.keyword_sentences)} sentences")
        

    def flat_keywords(self, result: KeywordExtractionResult) -> List[str]:
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
        cached = self._get_cached_result(cache_key)
        if cached:
            return self.flat_keywords(cached)
        return None


    def clear_cache(self, job_description: str) -> bool:
        """Clear cached result for a specific job description"""

        cache_key = self._get_cache_key(job_description)
        try: 
            pattern = f"resume:cache:{cache_key}"
            keys = list(redis_client.scan_iter(match=pattern))
            if keys:
                redis_client.delete(*keys)
                return True

        except Exception as e:
            print(f"Cache clear failed: {e}")
        return False