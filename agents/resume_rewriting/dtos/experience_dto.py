from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class ExperienceItem(BaseModel):
    title: str = Field(..., description="The job title or position held.")
    company: str = Field(..., description="The name of the company or organization.")
    duration: str = Field(..., description= "time worked at a particular organization")
    location: Optional[str] = Field(default = None, description="The location of the job, if available.")
    start_date: Optional[str] = Field(default = None, description="The start date of the job in YYYY-MM format.")
    end_date: Optional[str] = Field(default = None, description="The end date of the job in YYYY-MM format, or 'Present' if currently employed.")
    bullet_points: List[str] = Field(description="A brief description of the role and responsibilities.")
    skills_demonstrated: List[str] = Field(default_factory=list, description="A list of skills demonstrated in this role.")

class ExperienceStructured(BaseModel):
    experiences: List[ExperienceItem] = Field(..., description="A list of structured experience items extracted from the resume.")
    total_experiences: int = Field(..., description="Total number of experiences extracted from the resume.")
    total_bullet_points: int = Field(..., description="Total number of bullet points across all experiences.")
    skills_used: List[str] = Field(default_factory=list, description="A list of unique skills used across all experiences.")
    keywords_matched: Optional[List[str]]= Field(default_factory=list, description="A list of keywords matched from the job description.")
    keywords_missing: Optional[List[str]] = Field(default_factory=list, description="A list of keywords from the job description that were not found in the experiences.")
    match_score: Optional[float] = Field(default = 0.0, description="A score representing how well the experiences match the job description, if applicable.")

class ExperienceWriterKeywordUsage(BaseModel):
    keywords_incorporated: List[str] = Field(default_factory=list, description="Keywords that appear in the rewrite.")
    keywords_missing: List[str] = Field(default_factory=list, description="Keywords that do not appear.")

class ExperienceWriterResponse(BaseModel):
    content: str = Field(..., description="Full rewritten experience section as markdown.")
    experiences: List[ExperienceItem] = Field(..., description="Rewritten per-role entries.")
    keyword_usage: ExperienceWriterKeywordUsage = Field(
        default_factory=ExperienceWriterKeywordUsage,
        description="Which keywords were incorporated vs. missing.",
    )
    total_bullet_points: int = Field(default=0, description="Total bullet points across all entries.")
    skills_used: List[str] = Field(default_factory=list, description="Union of skills across all entries.")
    match_score: float = Field(default=0.0, description="Match score against the job description.")


class ExperienceAgentOutput(BaseAgentOutput):
    content: str = Field(..., description="The main content or output produced by the experience extraction agent.")
    structured: ExperienceStructured = Field(..., description="Structured representation of the output, including experiences and related metrics.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")