import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List 
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from .config import SKILLS_MODEL
from .prompts import (
    SKILLS_WRITER_SYSTEM_PROMPT,
    SKILLS_WRITER_HUMAN_PROMPT,
    SKILLS_WRITER_PROMPT_VERSION
)
from .dtos import (
    SkillsAgentOutput,
    SkillsStructured,
    SkillsWriterResponse,
    AgentMetadata,
)
from agents.resume_rewriting.pipeline._helpers import format_notes
from infrastructure.llm_client import call_llm
from infrastructure.redis_service import redis_service

load_dotenv()
_skills_chain = None
def _get_skills_chain(model: str):
    global _skills_chain
    if _skills_chain is None:
            llm = ChatGroq(
                model = model,
                api_key = os.getenv("SKILLS_MODEL"),
                temperature= 0.5
            ).with_structured_output(
                SkillsWriterResponse,
                method="json_schema",
                include_raw=True
            )
            chain = ChatPromptTemplate.from_messages([
                ("system", SKILLS_WRITER_SYSTEM_PROMPT),
                ("human", SKILLS_WRITER_HUMAN_PROMPT),
            ])
            _skills_chain = chain| llm
    
    return _skills_chain

def rewrite_skills(
    skills: SkillsStructured,
    job_description: str,
    keywords: List[str],
    run_id: str,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
    model: str = SKILLS_MODEL,
    revision_notes: Optional[List[str]] = None,
) -> SkillsAgentOutput:
    start_time = datetime.now()
    if not job_description or not job_description.strip():
        raise ValueError("Job description is empty.")
    if not skills:
        raise ValueError("No Skills to rewrite.")


    redis_service.set_job_status(run_id, "processing", "Skills writer started")

    if isinstance(skills, dict):
        skills_str = "\n".join(
            f"{category}: {', '.join(items)}"
            for category, items in skills.items()
        )
    elif isinstance(skills, list):
        skills_str = ", ".join(str(s) for s in skills)
    else:
        skills_str = str(skills)

    chain = _get_skills_chain(model)
    prompt_inputs = {
            "job_description": job_description,
            "skills": skills_str,
            "keywords": ", ".join(keywords) if keywords else "None",
            "must_have": ", ".join(must_have) if must_have else "None specified",
            "nice_to_have": ", ".join(nice_to_have) if nice_to_have else "None specified",
            "revision_notes": format_notes(revision_notes),
        }

    result = call_llm(
        chain=chain,
        prompt_inputs=prompt_inputs,
        run_id=run_id,
        agent="skills",
        role="writer",
        prompt_version=SKILLS_WRITER_PROMPT_VERSION,
        model=model,
        temperature=0.5,
        )
    if result.error or result.response is None:
        error_msg = f"skills rewriting failed: {result.error or 'no response'}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg)
    
    parsed = result.response 
    keyword_usage = parsed.get("keyword_usage", {})
    structured = SkillsStructured(
                categories=parsed.get("categories", {}),
                total_skills=parsed.get("total_skills", 0),
                keywords_matched=keyword_usage.get("keywords_incorporated", []),
                keywords_missing=keyword_usage.get("keywords_missing", []),            
            )
    dto = SkillsAgentOutput(
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
    redis_service.store_job_data(run_id, "skills_agent_output", dto.model_dump())
    redis_service.set_job_status(run_id, "completed", "Skills writer completed")

    return dto