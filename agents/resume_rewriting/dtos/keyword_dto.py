from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class KeywordSentence(BaseModel):
    sentence: str = Field(..., description="The sentence extracted from the job description.")
    keywords: List[str] = Field(..., description="List of keywords extracted from the sentence.")

class KeywordContent(BaseModel):
    keywords: List[str] = Field(..., description="List of unique keywords extracted from the job description.")
    keyword_sentences: List[KeywordSentence] = Field(..., description="List of sentences with their extracted keywords.")

class KeywordStructured(BaseModel):
    flat_keywords: List[str] = Field(..., description="Flattened list of unique keywords extracted from the job description.")
    keyword_count: int = Field(..., description="Count of unique keywords extracted from the job description.")
    sentence_count: int = Field(..., description="Count of sentences processed for keyword extraction.")
    categorized_keywords: Optional[dict] = Field(default = None, description="Optional categorization of keywords (industry-specific)")

class KeywordAgentOutput(BaseAgentOutput):
    content: KeywordContent = Field(..., description="The main content or output produced by the keyword extraction agent.")
    structured: KeywordStructured = Field(..., description="Structured representation of the output, including flattened keywords and counts.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")
