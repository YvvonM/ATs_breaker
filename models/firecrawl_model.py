from pydantic import BaseModel, Field
from typing import Any, List, Optional


class FirecrawlJobSchema(BaseModel):
    title: str = Field(description = "The job title")
    company: str = Field(description = "The company name")
    location: Optional[str] = Field(default = None, description = "Job location")
    is_remote: bool = Field(default=False, description = "Whether the job is remote")
    employment_type: Optional[str] = Field(default=None, description = "Employment type (e.g., full-time, part-time)")
    seniority: Optional[str] = Field(default=None, description = "Seniority level (e.g., junior, mid, senior)")
    description: Optional[str] = Field(default=None, description = "Full Job description")
    requirements: Optional[List[str]] = Field(default=None, description="List of job requirements or qualifications")
    salary_min: Optional[float] = Field(default=None, description="Minimum salary if mentioned")
    salary_max: Optional[float] = Field(default=None, description="Maximum salary if mentioned")
    salary_currency: Optional[str] = Field(default=None, description="Salary currency, e.g. USD, EUR")
    visa_sponsorship: bool = Field(default=False, description="Whether visa sponsorship is mentioned")
    