from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentOutput, AgentMetadata

class EducationItem(BaseModel):
    degree: str = Field(..., description="The degree or certification obtained.")
    institution: str = Field(..., description="The name of the educational institution.")
    location: Optional[str] = Field(None, description="The location of the institution, if available.")
    duration: Optional[str] = Field(None, description="The duration of the education in YYYY-MM format or a descriptive string.")
    field_of_study: Optional[str] = Field(None, description="The field of study or major, if applicable.")
    related_courses: Optional[List[str]] = Field(default=[], description="A list of related courses or subjects studied, if applicable.")

class EducationStructured(BaseModel):
    educations: List[EducationItem] = Field(..., description="A list of structured education items extracted from the resume.")
    highest_degree: Optional[str] = Field(None, description="The highest degree obtained, if applicable.")
    total_educations: int = Field(..., description="Total number of education items extracted from the resume.")


class EducationAgentOutput(BaseAgentOutput):
    content: List[EducationItem] = Field(..., description="The main content or output produced by the education extraction agent.")
    structured: EducationStructured = Field(..., description="Structured representation of the output, including educations and related metrics.")
    metadata: AgentMetadata = Field(..., description="Metadata related to the agent's execution and output.")