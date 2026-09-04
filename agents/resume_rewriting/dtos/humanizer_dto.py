from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class ChangesSummary(BaseModel):
    """Summary of changes made"""
    sentences_rewritten: int = Field(description="Number of sentences rewritten")
    words_added: int = Field(description="Number of words added")
    words_removed: int = Field(description="Number of words removed")
    tone_adjustments: List[str] = Field(description="Tone adjustments made")
    personal_pronouns_added: int = Field(description="Number of personal pronouns added")

class StyleMetrics(BaseModel):
    """Style metrics for the humanized resume"""
    readability_score: float = Field(description="Readability score (0-100)")
    avg_sentence_length: float = Field(description="Average sentence length in words")
    complexity: str = Field(description="Complexity level (low, medium, high)")
    tone: str = Field(description="Detected tone of the text")

class HumanizerStructured(BaseModel):
    """Structured data for humanizer agent"""
    changes_summary: ChangesSummary = Field(description="Summary of changes made")
    style_metrics: StyleMetrics = Field(description="Style metrics")

class HumanizerAgentOutput(BaseAgentOutput):
    """Complete output from Humanizer Agent"""
    content: str = Field(description="Final humanized resume text")
    structured: HumanizerStructured = Field(description="Structured humanizer data")
    metadata: AgentMetadata = Field(description="Execution metadata")