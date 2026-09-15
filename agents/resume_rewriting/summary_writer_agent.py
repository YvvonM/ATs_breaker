import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List, Dict, Any
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import SUMMARY_MODEL, MAX_SKILLS_PER_CATEGORY, MAX_EXPERIENCES
from .prompts import (
    SUMMARY_WRITER_SYSTEM_PROMPT,
    SUMMARY_WRITER_HUMAN_PROMPT,
)
from .dtos import (
    SummaryAgentOutput,
    SummaryStructured,
    ExperienceStructured,
    SkillsStructured,
    AgentMetadata,
)
from infrastructure.redis_service import redis_service

load_dotenv()
_summary_chain = None

def _get_summary_chain(model: str):
    global _summary_chain
    if _summary_chain is None:
        llm = ChatGroq(
                model = model,
                api_key = os.getenv("SUMMARY_MODEL"),
                temperature= 0.5
                )
        chain = ChatPromptTemplate.from_messages([
                ("system", SUMMARY_WRITER_SYSTEM_PROMPT),
                ("human", SUMMARY_WRITER_HUMAN_PROMPT),
                ])
        _summary_chain = chain| llm| JsonOutputParser()
        
    return _summary_chain

def _trim_experiences(
    experiences:List[Dict[str, Any]],
    max_count: int = MAX_EXPERIENCES
    )-> List[Dict[str, Any]]:
    return experiences[:max_count]

def _trim_skills_to_jd(
    categories: Dict[str, List[str]],
    keywords: List[str],
    max_per_categories: int = MAX_SKILLS_PER_CATEGORY
    ) -> Dict[str, List[str]]:
    keyword_set = (kw.lower().strip() for kw in keywords)
    trimmed: Dict[str, List[str]] = {}
    for category, items in categories.items():
        kept = [s for s in items if s.lower().strip() in keyword_set]
        if kept:
            trimmed[category] = kept[: max_per_categories]

    return trimmed

def rewrite_summary(
    original_summary: str,
    job_description: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    model: str = SUMMARY_MODEL,
) -> SummaryAgentOutput:
    start_time = datetime.now()
    if not job_description or not job_description.strip():
        raise ValueError("Job description is empty.")

    if run_id is None:
        run_id = redis_service.get_run_id()

    exp_data = redis_service.get_job_data(run_id, "experience_agent_output")
    skills_data = redis_service.get_job_data(run_id, "skills_agent_output")
    if not exp_data and not skills_data:
        missing = []
        if not exp_data:
            missing.append("experience")
        if not skills_data:
            missing.append("skills")

        error_msg = f"Missing Redis data for: {', '.join(missing)}. Run those pipelines first."
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg)

    all_experiences = exp_data["structured"].get("experiences", [])
    experiences_json = _trim_experiences(all_experiences)

    all_skills = skills_data["structured"].get("categories", {})
    skills_json = _trim_skills_to_jd(all_skills, keywords)

    redis_service.set_job_status(run_id, "processing", "Summary writer started")
    chain = _get_summary_chain(model)
    try:
        parsed = chain.invoke({
            "job_description": job_description,
            "experiences_json": experiences_json,
            "skills_json": skills_json,
            "original_summary": original_summary or "(none provided)",
            "keywords": ", ".join(keywords) if keywords else "None",
            
        })

    except Exception as e:
        error_msg = f"summary writing failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg) from e

    
    
    structured = SummaryStructured(
                summary_type= parsed.get('summary_type', ''),
                key_attributes= parsed.get('key_attributes', []),
                tone = parsed.get('tone', ''),
                target_role= parsed.get('target_role', ''),
                years_experience= parsed.get('years_experience', ''),
                keywords_incorporated= parsed.get('keywords_incorporated', []),
                word_count= parsed.get('word_count', 0) 
            )
    dto = SummaryAgentOutput(
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
    redis_service.store_job_data(run_id, "summary_agent_output", dto.model_dump())  # ← fixed
    redis_service.set_job_status(run_id, "completed", "Summary writer completed")   # ← fixed

    return dto
    