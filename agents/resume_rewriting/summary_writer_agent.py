import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List, Dict, Any
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from .config import SUMMARY_MODEL, MAX_SKILLS_PER_CATEGORY, MAX_EXPERIENCES
from .prompts import (
    SUMMARY_WRITER_SYSTEM_PROMPT,
    SUMMARY_WRITER_HUMAN_PROMPT,
    SUMMARY_WRITER_PROMPT_VERSION
)
from .dtos import (
    SummaryAgentOutput,
    SummaryStructured,
    ExperienceStructured,
    SkillsStructured,
    SummaryWriterResponse,
    AgentMetadata,
)
from agents.resume_rewriting.pipeline._helpers import format_notes
from infrastructure.llm_client import call_llm
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
                ).with_structured_output(
                    SummaryWriterResponse,
                    method="json_schema",
                    include_raw=True,

                )
        chain = ChatPromptTemplate.from_messages([
                ("system", SUMMARY_WRITER_SYSTEM_PROMPT),
                ("human", SUMMARY_WRITER_HUMAN_PROMPT),
                ])
        _summary_chain = chain| llm
        
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
    keyword_set = {kw.lower().strip() for kw in keywords}
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
    run_id:str,
    model: str = SUMMARY_MODEL,
    revision_notes: Optional[List[str]] = None,
) -> SummaryAgentOutput:
    start_time = datetime.now()
    if not job_description or not job_description.strip():
        raise ValueError("Job description is empty.")


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
    prompt_inputs = {
            "job_description": job_description,
            "experiences_json": experiences_json,
            "skills_json": skills_json,
            "original_summary": original_summary or "(none provided)",
            "keywords": ", ".join(keywords) if keywords else "None",
            "revision_notes": format_notes(revision_notes),
        }

    result = call_llm(
        chain=chain,
        prompt_inputs=prompt_inputs,
        run_id=run_id,
        agent="summary",
        role="writer",
        prompt_version=SUMMARY_WRITER_PROMPT_VERSION,
        model=model,
        temperature=0.5,
        )
    if result.error or result.response is None:
        error_msg = f"summary rewriting failed: {result.error or 'no response'}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg)
    
    parsed = result.response 
    
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
            token_count=result.usage.total,
            status="completed",
            started_at=start_time,
            completed_at=datetime.now(),
        ),
        error=None,
    )
    redis_service.store_job_data(run_id, "summary_agent_output", dto.model_dump())  # ← fixed
    redis_service.set_job_status(run_id, "completed", "Summary writer completed")   # ← fixed

    return dto
    