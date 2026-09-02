from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class ExperienceItem(BaseModel):
    title: str = Field(..., description="The job title or position held.")
    company: str = Field(..., description="The name of the company or organization.")
    location: Optional[str] = Field(None, description="The location of the job, if available.")
    start_date: Optional[str] = Field(None, description="The start date of the job in YYYY-MM format.")
    end_date: Optional[str] = Field(None, description="The end date of the job in YYYY-MM format, or 'Present' if currently employed.")
    bullet_points: List[str] = Field(description="A brief description of the role and responsibilities.")
    skills_demostrated: List[str] = Field(default=[], description="A list of skills demonstrated in this role.")

class ExperienceStructured(BaseModel):
    experiences: List[ExperienceItem] = Field(..., description="A list of structured experience items extracted from the resume.")
    total_experiences: int = Field(..., description="Total number of experiences extracted from the resume.")
    total_bullet_points: int = Field(..., description="Total number of bullet points across all experiences.")
    skills_used: List[str] = Field(default=[], description="A list of unique skills used across all experiences.")
    keywords_matched: Optional[List[str]]= Field(default=[], description="A list of keywords matched from the job description.")
    keywordss_missing: Optional[List[str]] = Field(default=[], description="A list of keywords from the job description that were not found in the experiences.")
    match_score: Optional[float] = Field(None, description="A score representing how well the experiences match the job description, if applicable.")


class ExperienceAgentOutput(BaseAgentOutput):
    content: List[ExperienceItem] = Field(..., description="The main content or output produced by the experience extraction agent.")
    structured: ExperienceStructured = Field(..., description="Structured representation of the output, including experiences and related metrics.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")