from typing import List, Optional
from pydantic import BaseModel, Field
from dtos.base import BaseAgentOutput, AgentMetadata

class ProjectItem(BaseModel):
    """Single project entry"""
    name: str = Field(description="Project name")
    description: str = Field(description="Brief project description")
    skills_demonstrated: List[str] = Field(description="Skills shown in this project")
    achievements: List[str] = Field(description="Key achievements/results")

class ProjectsStructured(BaseModel):
    """Structured data for projects agent"""
    projects: List[ProjectItem] = Field(description="All project entries")
    total_projects: int = Field(description="Total number of projects")
    skills_used: List[str] = Field(description="All skills mentioned across projects")
    project_types: List[str] = Field(default=[], description="Types of projects")

class ProjectsAgentOutput(BaseAgentOutput):
    """Complete output from Projects Agent"""
    content: str = Field(description="Full projects section as markdown text")
    structured: ProjectsStructured = Field(description="Structured projects data")
    metadata: AgentMetadata = Field(description="Execution metadata")