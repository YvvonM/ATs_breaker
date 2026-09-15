import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional, List
from datetime import datetime

from .skills_parser_agent import parse_skills
from .skill_writer_agent import rewrite_skills
from .dtos import SkillsAgentOutput, SkillsStructured, AgentMetadata
from infrastructure.redis_service import redis_service


def process_skills(
    job_description: str,
    skills_section: str,
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
) -> SkillsAgentOutput:
    start_time = datetime.now()

    if run_id is None:
        run_id = redis_service.get_run_id() or str(uuid.uuid4())

    try:
        print(f"[{run_id}] Parsing skills section...")
        skills = parse_skills(skills_section)
        print(f"[{run_id}] Parsed {skills.total_skills} skills")
        print(f"[{run_id}] Rewriting for the job description...")

        dto = rewrite_skills(
            skills=skills,
            job_description=job_description,
            keywords=keywords,
            run_id=run_id,
            must_have=must_have,
            nice_to_have=nice_to_have,
        )
        return dto

    except Exception as e:
        error_msg = f"Skills pipeline failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        return SkillsAgentOutput(
            content="",
            structured=SkillsStructured(
                categories={},
                total_skills=0,
                keywords_matched=[],
                keywords_missing=[],
            ),
            metadata=AgentMetadata(
                model_used="pipeline",
                execution_time=(datetime.now() - start_time).total_seconds(),
                token_count=0,
                status="failed",
                started_at=start_time,
                completed_at=datetime.now(),
            ),
            error={"message": error_msg},
        )