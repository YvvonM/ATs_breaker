from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class SkillsStructured(BaseModel):
    """Structured data for skills agent"""
    categories: Dict[str, List[str]] = Field(
        description="Skills organized by category (dynamic - industry specific)"
    )
    total_skills: int = Field(description="Total number of skills")
    keywords_matched: List[str] = Field(description="Keywords from JD that were incorporated")
    keywords_missing: List[str] = Field(description="Keywords from JD that are missing")

class SkillsAgentOutput(BaseAgentOutput):
    """Complete output from Skills Agent"""
    content: str = Field(description="Full skills section as markdown text")
    structured: SkillsStructured = Field(description="Structured skills data")
    metadata: AgentMetadata = Field(description="Execution metadata")