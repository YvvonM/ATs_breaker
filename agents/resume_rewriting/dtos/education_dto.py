from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class EducationItem(BaseModel):
    degree: str = Field(default= "", description="The degree or certification obtained.")
    institution: str = Field(default= "", description="The name of the educational institution.")
    location: Optional[str] = Field(default=None, description="The location of the institution, if available.")
    duration: Optional[str] = Field(default=None, description="The duration of the education in YYYY-MM format or a descriptive string.")
    field_of_study: Optional[str] = Field(default=None, description="The field of study or major, if applicable.")
    related_courses: Optional[List[str]] = Field(default_factory=list, description="A list of related courses or subjects studied, if applicable.")

class EducationStructured(BaseModel):
    educations: List[EducationItem] = Field(..., description="A list of structured education items extracted from the resume.")
    highest_degree: Optional[str] = Field(None, description="The highest degree obtained, if applicable.")
    total_educations: int = Field(..., description="Total number of education items extracted from the resume.")


class EducationWriterResponse(BaseModel):
    education: List[EducationItem] = Field(
        description="Rewritten education entries.",
    )
    highest_degree: Optional[str] = Field(
        default=None,
        description="Highest-ranked degree across all entries, as written.",
    )
    total_educations: int = Field(
        default=0,
        description="Count of entries in `education`.",
    )

class EducationAgentOutput(BaseAgentOutput):
    content: List[EducationItem] = Field(..., description="The main content or output produced by the education extraction agent.")
    structured: EducationStructured = Field(..., description="Structured representation of the output, including educations and related metrics.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")