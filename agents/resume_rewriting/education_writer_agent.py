import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List, Dict, Any
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import EDUCATION_MODEL
from .prompts import (
    EDUCATION_WRITER_SYSTEM_PROMPT,
    EDUCATION_WRITER_HUMAN_PROMPT,
)
from .dtos import (
    EducationItem,
    EducationAgentOutput,
    EducationStructured,
    AgentMetadata
)
from infrastructure.redis_service import redis_service

load_dotenv()
_education_chain = None
def _get_education_chain(model: str):
    global _education_chain
    if _education_chain is None:
        llm = ChatGroq(
            model = model,
            api_key = os.getenv("EDUCATION_MODEL"),
            temperature= 0.5
            )
        chain = ChatPromptTemplate.from_messages([
                ("system", EDUCATION_WRITER_SYSTEM_PROMPT),
                ("human", EDUCATION_WRITER_HUMAN_PROMPT),
            ])
        _education_chain = chain| llm| JsonOutputParser()
    
    return _education_chain


def rewrite_education(
    education: List[EducationItem],
    job_description: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    model: str = EDUCATION_MODEL,
) -> EducationAgentOutput:
    start_time = datetime.now()
    if not education:
        raise ValueError("Job description is empty.")
    if run_id is None:
        run_id = redis_service.get_run_id()

    redis_service.set_job_status(run_id, "processing", "Education writer started")
    education_json = [
        {
            "degree": e.degree,
            "institution": e.institution,
            "duration": e.duration,
            "location": e.location,
            "field_of_study": e.field_of_study,
            "related_courses": e.related_courses
        }
        for e in education
    ]
    chain = _get_education_chain(model)
    try:
        parsed = chain.invoke({
            "job_description": job_description,
            "education_json": education_json,
            "keywords": ", ".join(keywords) if keywords else "None",
           
        })

    except Exception as e:
        error_msg = f"Education rewriting failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg) from e

    rewritten_education = [
        EducationItem(
            degree=edu.get("degree", ""),
            institution=edu.get("institution", ""),
            duration=edu.get("duration", ""),
            location=edu.get("location", ''),
            field_of_study=edu.get("field_of_study", []),
            related_courses=edu.get("related_courses", []),
        )
        for edu in parsed.get('education', [])
    ]
    structured = EducationStructured(
        educations=rewritten_education,
        highest_degree=parsed.get('highest_degree', ''),
        total_educations=parsed.get("total_educations", len(rewritten_education)),
    )
    dto = EducationAgentOutput(
        content=rewritten_education,
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
    redis_service.store_job_data(run_id, "education_agent_output", dto.model_dump())
    redis_service.set_job_status(run_id, "completed", "Education writer completed")

    return dto