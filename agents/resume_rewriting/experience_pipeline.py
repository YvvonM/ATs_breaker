import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import Optional, List
from datetime import datetime
from .experience_parser_agent import parse_experience
from .experience_writer_agent import rewrite_experience
from .dtos import (
    ExperienceAgentOutput, 
    ExperienceStructured, 
    AgentMetadata
)
from infrastructure.redis_service import redis_service

def process_experience(
    job_description: str,
    experience_section: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
)-> ExperienceAgentOutput:
    start_time = datetime.now()
    if run_id is None:
        run_id = redis_service.get_run_id()

    try:
        print('Parsing experience section...')
        experiences = parse_experience(experience_section)
        print(f'Parsed {len(experiences)} experiences')
        print('Rewriting for the job description...')

        dto = rewrite_experience(
            experiences=experiences,
            job_description=job_description,
            keywords=keywords,
            run_id=run_id,
            must_have=must_have,
            nice_to_have=nice_to_have,
        )
        return dto
    except Exception as e:
        error_msg = f"Experience pipeline failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        return ExperienceAgentOutput(
            content="",
            structured=ExperienceStructured(
                experiences=[], total_experiences=0, total_bullet_points=0,
                skills_used=[], keywords_matched=[], keywords_missing=[], match_score=0.0,
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

 

