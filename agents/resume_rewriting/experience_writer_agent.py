import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List 
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import EXPERIENCE_MODEL
from .prompts import (
    EXPERIENCE_WRITER_SYSTEM_PROMPT,
    EXPERIENCE_WRITER_HUMAN_PROMPT,
)
from .dtos import (
    ExperienceAgentOutput,
    ExperienceStructured,
    ExperienceItem,
    AgentMetadata,
)
from infrastructure.redis_service import redis_service

load_dotenv()
_writer_chain = None

def _get_writer_chain(model: str):
    if _writer_chain is None:
        llm = ChatGroq(
            model = model,
            api_key = os.getenv("EXPEREINCE_WRITER"),
            temperature= 0.5
        )
        chain = ChatPromptTemplate.from_messages([
            ("system", EXPERIENCE_WRITER_SYSTEM_PROMPT),
            ("human", EXPERIENCE_WRITER_HUMAN_PROMPT),
        ])
        _writer_chain = chain| llm| JsonOutputParser()

    return _writer_chain

def rewrite_experience(
    experiences: List[ExperienceItem],
    job_description: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
    model: str = EXPERIENCE_MODEL,
) -> ExperienceAgentOutput:
    start_time = datetime.now()
    if not job_description or job_description.strip():
        raise ValueError("Job description is empty.")
    if not experiences:
        raise ValueError("No experiences to rewrite.")

    if run_id is None:
        run_id = redis_service.get_run_id()

    redis_service.set_job_status(run_id, "processing", "Experience writer started")
    experiences_json = [
        {
            "company": e.company,
            "title": e.title,
            "duration": e.duration,
            "location": e.location,
            "bullet_points": e.bullet_points,
        }
        for e in experiences
    ]
    chain = _get_writer_chain(model)
    try:
        parsed = chain.invoke({
            "job_description": job_description,
            "experiences_json": experiences_json,
            "keywords": ", ".join(keywords) if keywords else "None",
            "must_have": ", ".join(must_have) if must_have else "None specified",
            "nice_to_have": ", ".join(nice_to_have) if nice_to_have else "None specified",
        })

    except Exception as e:
        error_msg = f"Experience rewriting failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg) from e

    rewritten_experiences = [
        ExperienceItem(
            company=exp.get("company", ""),
            title=exp.get("title", ""),
            duration=exp.get("duration", ""),
            location=exp.get("location"),
            bullet_points=exp.get("bullet_points", []),
            skills_demonstrated=exp.get("skills_demonstrated", []),
        )
        for exp in parsed.get('experinces', [])
    ]
    keyword_usage = parsed.get("keyword_usage", {})
    structured = ExperienceStructured(
        experiences=rewritten_experiences,
        total_experiences=len(rewritten_experiences),
        total_bullet_points=parsed.get("total_bullet_points",
                                      sum(len(e.bullet_points) for e in rewritten_experiences)),
        skills_used=parsed.get("skills_used", []),
        keywords_matched=keyword_usage.get("keywords_incorporated", []),
        keywords_missing=keyword_usage.get("keywords_missing", []),
        match_score=parsed.get("match_score", 0.0),
    )
    dto = ExperienceAgentOutput(
        content=parsed.get("content", ""),
        structured=structured,
        metadata=AgentMetadata(
            model_used=model,
            execution_time=(datetime.now() - start_time).total_seconds(),
            token_count=0,
            status="completed",
            started_at=start_time,
            completed_at=datetime.now(),
        ),
        error=None,
    )
    redis_service.store_job_data(run_id, "experience_agent_output", dto.model_dump())
    redis_service.set_job_status(run_id, "completed", "Experience writer completed")

    return dto