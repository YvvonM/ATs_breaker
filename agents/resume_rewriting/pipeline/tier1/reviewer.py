from __future__ import annotations
import os 
import logging
import json 
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from .prompts import (
    TIER1_REVIEWER_SYSTEM_PROMPT,
    TIER1_REVIEWER_HUMAN_PROMPT,
    TIER1_REVIEWER_PROMPT_VERSION
)
from agents.resume_rewriting.dtos import Tier1ReviewerResponse
from infrastructure.llm_client import call_llm


load_dotenv()
logger = logging.getLogger(__name__)

_SCORE_KEYS = ("relevance", "clarity", "impact", "keyword_coverage")
_reviewer_chain = None

def _get_reviewer_chain(model: str):
    global _reviewer_chain
    if _reviewer_chain is None:
        llm = ChatGroq(
                model = model,
                api_key = os.getenv("REVIEWER_MODEL"),
                temperature= 0.1
                ).with_structured_output(
                    Tier1ReviewerResponse,
                    method="json_schema",
                    include_raw=True,

                )
        chain = ChatPromptTemplate.from_messages([
                ("system", TIER1_REVIEWER_SYSTEM_PROMPT),
                ("human", TIER1_REVIEWER_HUMAN_PROMPT),
                ])
        _reviewer_chain = chain| llm
        
    return _reviewer_chain

@dataclass
class ReviewResult:
    decision: str
    scores: Dict[str, float] = field(default_factory=dict)
    feedback: Dict[str, List[str]] = field(default_factory=dict)
    revision_notes: List[str] = field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None
    token_count:int = 0
    error: Optional[str] = None

class Tier1Reviewer:
    def __init__(self, model:str) -> None:
        self.model = model

    def review(self, *, agent, section_content, section_structured,
               job_description, keywords, run_id) -> ReviewResult:
        chain = _get_reviewer_chain(self.model)
        prompt_inputs ={
            "agent": agent,
            "job_description": job_description,
            "keywords": ", ".join(keywords) if keywords else "None",
            "section_content": section_content,
            "section_structured": json.dumps(
                section_structured, indent=2, default=str
            ),
        }
        result = call_llm(
            chain=chain,
            prompt_inputs=prompt_inputs,
            run_id=run_id,
            agent=agent,
            role="reviewer",
            prompt_version=TIER1_REVIEWER_PROMPT_VERSION,
            model=self.model,
            temperature=0.1,
            )

        if result.error or result.response is None:
                logger.warning(
                    "Tier1 reviewer failed for agent=%s run=%s: %s",
                    agent,
                    run_id,
                    result.error or "no response",
                )
                return ReviewResult(
                    decision="accept",
                    error=result.error or "no response",
                )

        parsed = result.response
        raw_scores = parsed.get("scores") or {}
        scores = {key: float(raw_scores.get(key, 0.0)) for key in _SCORE_KEYS}

        return ReviewResult(
            decision=parsed.get("decision", "accept"),
            scores=scores,
            feedback=parsed.get("feedback") or {},
            revision_notes=(parsed.get("revision_notes") or [])[:5],
            token_count=result.usage.total,
            raw=parsed,
            error=None,
        )

    