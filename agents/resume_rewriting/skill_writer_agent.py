import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List 
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import SKILLS_MODEL
from .prompts import (
    SKILLS_WRITER_SYSTEM_PROMPT,
    SKILLS_WRITER_HUMAN_PROMPT,
)
from .dtos import (
    SkillsAgentOutput,
    SkillsStructured,
    AgentMetadata,
)
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
            )
            chain = ChatPromptTemplate.from_messages([
                ("system", SKILLS_WRITER_SYSTEM_PROMPT),
                ("human", SKILLS_WRITER_HUMAN_PROMPT),
            ])
            _skills_chain = chain| llm| JsonOutputParser()
    
    return _skills_chain

def rewrite_skills(
    skills: SkillsStructured,
    job_description: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
    model: str = SKILLS_MODEL,
) -> SkillsAgentOutput:
    start_time = datetime.now()
    if not job_description or not job_description.strip():
        raise ValueError("Job description is empty.")
    if not skills:
        raise ValueError("No Skills to rewrite.")

    if run_id is None:
        run_id = redis_service.get_run_id()

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
    try:
        parsed = chain.invoke({
            "job_description": job_description,
            "skills": skills_str,
            "keywords": ", ".join(keywords) if keywords else "None",
            "must_have": ", ".join(must_have) if must_have else "None specified",
            "nice_to_have": ", ".join(nice_to_have) if nice_to_have else "None specified",
        })

    except Exception as e:
        error_msg = f"skills rewriting failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg) from e

    
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
            token_count=0,
            status="completed",
            started_at=start_time,
            completed_at=datetime.now(),
        ),
        error=None,
    )
    redis_service.store_job_data(run_id, "skills_agent_output", dto.model_dump())
    redis_service.set_job_status(run_id, "completed", "Skills writer completed")

    return dto