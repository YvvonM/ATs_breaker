from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .keyword_dto import KeywordAgentOutput
from .experience_dto import ExperienceAgentOutput
from .education_dto import EducationAgentOutput
from .skills_dto import SkillsAgentOutput
from .summary_dto import SummaryAgentOutput
from .project_dto import ProjectsAgentOutput
from .manager_dto import ManagerAgentOutput
from .humanizer_dto import HumanizerAgentOutput

class AllAgentsOutputs(BaseModel):
    """Aggregated outputs from all agents"""
    # Use consistent naming with _agent suffix
    keyword_agent: Optional[KeywordAgentOutput] = Field(
        default=None, 
        description="Output from Keyword Agent"
    )
    experience_agent: Optional[ExperienceAgentOutput] = Field(
        default=None, 
        description="Output from Experience Agent"
    )
    education_agent: Optional[EducationAgentOutput] = Field(
        default=None, 
        description="Output from Education Agent"
    )
    skills_agent: Optional[SkillsAgentOutput] = Field(
        default=None, 
        description="Output from Skills Agent"
    )
    summary_agent: Optional[SummaryAgentOutput] = Field(
        default=None, 
        description="Output from Summary Agent"
    )
    projects_agent: Optional[ProjectsAgentOutput] = Field(
        default=None, 
        description="Output from Projects Agent"
    )
    manager_agent: Optional[ManagerAgentOutput] = Field(
        default=None, 
        description="Output from Manager Agent"
    )
    humanizer_agent: Optional[HumanizerAgentOutput] = Field(
        default=None, 
        description="Output from Humanizer Agent"
    )
    def get_agent_names(self) -> list:
        """Get list of all agent names"""
        return [
            "keyword_agent",
            "experience_agent",
            "education_agent",
            "skills_agent",
            "summary_agent",
            "projects_agent",
            "manager_agent",
            "humanizer_agent",
        ]

    def get_agent_output(self, agent_name: str):
        """Helper to get output for a specific agent"""
        agent_map = {
            "keyword_agent": self.keyword_agent,
            "experience_agent": self.experience_agent,
            "education_agent": self.education_agent,
            "skills_agent": self.skills_agent,
            "summary_agent": self.summary_agent,
            "projects_agent": self.projects_agent,
            "manager_agent": self.manager_agent,
            "humanizer_agent": self.humanizer_agent,
        }
        return agent_map.get(agent_name)

    def get_completed_agents(self) -> list:
        """Get list of agents that have completed"""
        completed = []
        for name in self.get_agent_names():
            output = self.get_agent_output(name)
            if output and output.metadata.status == "completed":
                completed.append(name)
        return completed
    
    def to_dict(self) -> dict:
        """Convert to dict, excluding None values"""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    
class CVGenerationData(BaseModel):
    run_id: str = Field(description="Unique identifier for the CV generation run")
    application_id: str = Field(description="Unique identifier for the application")
    job_description: str = Field(description="Job description text")
    master_cv: str = Field(description="Master CV text")
    agent_outputs: AllAgentsOutputs = Field(description="Aggregated outputs from all agents")
    generated_resume: Optional[str] = Field(default=None, description="Final generated CV text")
    status: str = Field(description="Status of the CV generation process (e.g., 'completed', 'in_progress', 'failed')")
    current_step: Optional[str] = Field(default=None, description="Current step in the CV generation process")
    progress: Optional[float] = Field(default=None, description="Progress percentage of the CV generation process")
    error_message: Optional[str] = Field(default=None, description="Error message if the process failed")

    total_llm_calls: Optional[int] = Field(default=None, description="Total number of LLM calls made during the process")
    total_tokens: Optional[int] = Field(default=None, description="Total number of tokens used during the process")
    models_used: Optional[Dict[str, Any]] = Field(default=None, description="Details of models used during the process")
    created_at: Optional[str] = Field(default=None, description="Timestamp when the CV generation process was initiated")
    updated_at: Optional[str] = Field(default=None, description="Timestamp when the CV generation process was last updated")
    completed_at: Optional[str] = Field(default=None, description="Timestamp when the CV generation process was completed")

    
