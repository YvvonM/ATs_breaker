import sys 
import os 
import uuid 

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional, List
from datetime import datetime

from .project_parser_agent import parse_project
from .project_writer_agent import rewrite_projects
from .dtos import (
    ProjectsAgentOutput, 
    ProjectsStructured, 
    AgentMetadata
)
from infrastructure.redis_service import redis_service

def process_projects(
    project_section: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
)-> ProjectsAgentOutput:
    start_time = datetime.now()
    if run_id is None:
        run_id = redis_service.get_run_id()

    try:
        print('Parsing experience section...')
        projects = parse_project(project_section)
        print(f'Parsed {len(projects)} experiences')
        print('Rewriting for the job description...')

        dto = rewrite_projects(
            projects=projects,
            keywords=keywords,
            run_id=run_id,
            must_have=must_have,
            nice_to_have=nice_to_have,
        )
        return dto
    except Exception as e:
        error_msg = f"Experience pipeline failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        return ProjectsAgentOutput(
            content="",
            structured=ProjectsStructured(
                projects=[], total_projects=0, 
                skills_used=[],  project_types=[]
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

 

