from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class SummaryStructured(BaseModel):
    summary_type: str = Field(description="Type of summary (professional, executive, etc.)")
    key_attributes: List[str] = Field(default_factory= list, description="Key attributes highlighted in summary")
    tone: str = Field(description="Tone of the summary")
    target_role: Optional[str] = Field(default=None, description="Target role mentioned")
    years_experience: Optional[str] = Field(default=None, description="Years of experience mentioned")
    keywords_incorporated: List[str] = Field(description="Keywords incorporated from JD")
    word_count: int = Field(description="Word count of summary")

class SummaryWriterResponse(BaseModel):
    content: str = Field(..., description="Full rewritten summary text, plain string, no markdown headers.")
    summary_type: str = Field(..., description="Short label describing the summary's angle.")
    key_attributes: List[str] = Field(..., description="3-6 short phrases capturing core strengths.")
    tone: str = Field(..., description="One or two words describing the tone.")
    target_role: str = Field(..., description="Role title this summary is written for.")
    years_experience: str = Field(..., description="Inferred years of experience, e.g. '5+ years', or 'Not specified'.")
    keywords_incorporated: List[str] = Field(
        default_factory=list,
        description="Keywords from the provided list that appear in the summary.",
    )
    word_count: int = Field(default=0, description="Word count of the content field.")

class SummaryAgentOutput(BaseAgentOutput):
    """Complete output from Summary Agent"""
    content: str = Field(description="Full summary text")
    structured: SummaryStructured = Field(description="Structured summary data")
    metadata: AgentMetadata = Field(description="Execution metadata")