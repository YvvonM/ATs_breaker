from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class SkillsStructured(BaseModel):
    """Structured data for skills agent"""
    categories: Dict[str, List[str]] = Field(
        description="Skills organized by category (dynamic - industry specific)"
    )
    total_skills: int = Field(description="Total number of skills")
    keywords_matched: List[str] = Field(default_factory= list,description="Keywords from JD that were incorporated")
    keywords_missing: List[str] = Field(default_factory=list, description="Keywords from JD that are missing")
class SkillsWriterKeywordUsage(BaseModel):
    keywords_incorporated: List[str] = Field(
        default_factory=list,
        description="Keywords from the provided list that appear in the rewrite.",
    )
    keywords_missing: List[str] = Field(
        default_factory=list,
        description="Keywords from the provided list that do not appear in the rewrite.",
    )


class SkillsWriterResponse(BaseModel):
    content: str = Field(..., description="Full rewritten skills section as markdown.")
    categories: Dict[str, List[str]] = Field(
        ...,
        description="Skills grouped into categories (arbitrary string keys, list of skill strings).",
    )
    total_skills: int = Field(
        default=0,
        description="Total count of unique skills across all categories.",
    )
    keyword_usage: SkillsWriterKeywordUsage = Field(
        default_factory=SkillsWriterKeywordUsage,
        description="Which keywords were incorporated vs. missing.",
    )
class SkillsAgentOutput(BaseAgentOutput):
    """Complete output from Skills Agent"""
    content: str = Field(description="Full skills section as markdown text")
    structured: SkillsStructured = Field(description="Structured skills data")
    metadata: AgentMetadata = Field(description="Execution metadata")