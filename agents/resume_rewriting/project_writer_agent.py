import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from typing import  Optional, List 
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from .config import PROJECT_MODEL
from .prompts import (
    PROJECT_WRITER_SYSTEM_PROMPT,
    PROJECT_WRITER_HUMAN_PROMPT,
)
from .dtos import (
    ProjectsAgentOutput,
    ProjectsStructured,
    ProjectItem,
    AgentMetadata,
)
from infrastructure.redis_service import redis_service

load_dotenv()
_project_chain = None
def _get_project_chain(model:str):
    global _project_chain
    if _project_chain  is None:
        llm = ChatGroq(
            model = model,
            api_key = os.getenv("PROJECT_MODEL"),
            temperature= 0.5
                )
        chain = ChatPromptTemplate.from_messages([
                ("system", PROJECT_WRITER_SYSTEM_PROMPT),
                ("human", PROJECT_WRITER_HUMAN_PROMPT),
                ])
        _project_chain = chain| llm| JsonOutputParser()
        
    return _project_chain
    
def rewrite_projects(
    projects: List[ProjectItem],
    keywords: List[str],
    run_id: Optional[str] = None,
    must_have: Optional[List[str]] = None,
    nice_to_have: Optional[List[str]] = None,
    model: str = PROJECT_MODEL,
) -> ProjectsAgentOutput:
    start_time = datetime.now()
    if not projects:
        raise ValueError("No projects to rewrite.")

    if run_id is None:
        run_id = redis_service.get_run_id()

    redis_service.set_job_status(run_id, "processing", "Project writer started")
    projects_json = [
        {
            "name": p.name,
            "description": p.description,
            "skills_demonstrated": p.skills_demonstrated,
            "achievements": p.achievements,
            
        }
        for p in projects
    ]
    chain = _get_project_chain(model)
    try:
        parsed = chain.invoke({
            "projects_json": projects_json,
            "keywords": ", ".join(keywords) if keywords else "None",
            "must_have": ", ".join(must_have) if must_have else "None specified",
            "nice_to_have": ", ".join(nice_to_have) if nice_to_have else "None specified",
        })

    except Exception as e:
        error_msg = f"Projects rewriting failed: {e}"
        redis_service.set_job_status(run_id, "failed", error_msg)
        raise RuntimeError(error_msg) from e

    rewritten_projects = [
        ProjectItem(
            name=proj.get("name", ""),
            description=proj.get("description", ""),
            skills_demonstrated=proj.get("skills_demonstrated", []),
            achievements=proj.get("achievements", []),
            
        )
        for proj in parsed.get('projects', [])
    ]
    keyword_usage = parsed.get("keyword_usage", {})
    structured = ProjectsStructured(
        projects=rewritten_projects,
        total_projects=len(rewritten_projects),
        skills_used=parsed.get("skills_used", []),
        project_types=parsed.get('project_types', [])
    )
    dto = ProjectsAgentOutput(
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
    redis_service.store_job_data(run_id, "project_agent_output", dto.model_dump())
    redis_service.set_job_status(run_id, "completed", "Project writer completed")

    return dto