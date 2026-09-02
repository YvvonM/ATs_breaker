from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class SummaryStructured(BaseModel):
    summary_type: str = Field(description="Type of summary (professional, executive, etc.)")
    key_attributes: List[str] = Field(description="Key attributes highlighted in summary")
    tone: str = Field(description="Tone of the summary")
    target_role: Optional[str] = Field(default=None, description="Target role mentioned")
    years_experience: Optional[int] = Field(default=None, description="Years of experience mentioned")
    keywords_incorporated: List[str] = Field(description="Keywords incorporated from JD")
    word_count: int = Field(description="Word count of summary")

class SummaryAgentOutput(BaseAgentOutput):
    """Complete output from Summary Agent"""
    content: str = Field(description="Full summary text")
    structured: SummaryStructured = Field(description="Structured summary data")
    metadata: AgentMetadata = Field(description="Execution metadata")