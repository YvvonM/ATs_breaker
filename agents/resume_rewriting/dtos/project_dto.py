from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

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
    skills_used: List[str] = Field(default_factory=list, description="All skills mentioned across projects")
    project_types: List[str] = Field(default_factory=list, description="Types of projects")

class ProjectsWriterKeywordUsage(BaseModel):
    keywords_incorporated: List[str] = Field(
        default_factory=list,
        description="Keywords from the provided list that appear in the rewrite.",
    )
    keywords_missing: List[str] = Field(
        default_factory=list,
        description="Keywords from the provided list that do not appear in the rewrite.",
    )

class ProjectsWriterResponse(BaseModel):
    content: str = Field(..., description="Full rewritten projects section as markdown.")
    projects: List[ProjectItem] = Field(..., description="Rewritten per-project entries.")
    skills_used: List[str] = Field(
        default_factory=list,
        description="Union of all skills across rewritten projects.",
    )
    project_types: List[str] = Field(
        default_factory=list,
        description="Short labels describing each project's category.",
    )
    keyword_usage: ProjectsWriterKeywordUsage = Field(
        default_factory=ProjectsWriterKeywordUsage,
        description="Which keywords were incorporated vs. missing.",
    )

class ProjectsAgentOutput(BaseAgentOutput):
    """Complete output from Projects Agent"""
    content: str = Field(description="Full projects section as markdown text")
    structured: ProjectsStructured = Field(description="Structured projects data")
    metadata: AgentMetadata = Field(description="Execution metadata")