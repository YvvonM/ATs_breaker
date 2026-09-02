from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from dtos.base import BaseAgentOutput, AgentMetadata

class ReviewScores(BaseModel):
    """Review scores for the resume"""
    keyword_coverage: float = Field(description="Keyword coverage score (0-1)")
    relevance: float = Field(description="Relevance score (0-1)")
    clarity: float = Field(description="Clarity score (0-1)")
    impact: float = Field(description="Impact score (0-1)")
    overall: float = Field(description="Overall score (0-10)")

class ReviewFeedback(BaseModel):
    """Feedback from review"""
    strengths: List[str] = Field(description="Strengths identified")
    improvements: List[str] = Field(description="Areas for improvement")
    critical: List[str] = Field(description="Critical issues to address")

class ManagerContent(BaseModel):
    """Content for manager agent"""
    review_summary: str = Field(description="Summary of the review")
    improved_resume: str = Field(description="Full improved resume text")
    scores: ReviewScores = Field(description="Review scores")
    feedback: ReviewFeedback = Field(description="Detailed feedback")
    keywords_to_add: List[str] = Field(description="Keywords that should be added")
    sections_to_rewrite: List[str] = Field(description="Sections that need rewriting")

class ManagerStructured(BaseModel):
    """Structured data for manager agent"""
    final_score: float = Field(description="Final overall score (0-10)")
    recommendations: List[str] = Field(description="Actionable recommendations")
    status: str = Field(description="Status of the review (needs_improvement, good, excellent)")

class ManagerAgentOutput(BaseAgentOutput):
    """Complete output from Manager/QA Agent"""
    content: ManagerContent = Field(description="Review and improved resume")
    structured: ManagerStructured = Field(description="Structured review data")
    metadata: AgentMetadata = Field(description="Execution metadata")