import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Optional, List
from datetime import datetime
from .education_parser_agent import parse_education
from .education_writer_agent import rewrite_education
from .dtos import (
    EducationAgentOutput, 
    EducationStructured, 
    AgentMetadata
)
from infrastructure.redis_service import redis_service

def process_education(
    job_description: str,
    education_section: str,
    keywords: List[str],
    run_id: Optional[str] = None,
)-> EducationAgentOutput:
    start_time = datetime.now()
    if run_id is None:
        run_id = redis_service.get_run_id()

    try:
        print('Parsing education section...')
        education = parse_education(education_section)
        print(f'Parsed {len(education)} education')
        print('Rewriting for the education...')

        dto = rewrite_education(
            education=education,
            job_description=job_description,
            keywords=keywords,
            run_id=run_id,
            
        )
        return dto
    except Exception as e:
        error_msg = f"Education pipeline failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        return EducationAgentOutput(
            content=[],
            structured=EducationStructured(
                educations=[], highest_degree=None, total_educations=0,
                
            ),
            metadata=AgentMetadata(
                model_used="pipeline",
                execution_time=(datetime.now() - start_time).total_seconds(),
                token_count=0, status="failed",
                started_at=start_time, completed_at=datetime.now(),
            ),
            error= {
            "message": error_msg
        }
        )

 

