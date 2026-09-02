from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Application(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="job.id")
    company_id: UUID = Field(foreign_key="company.id")

    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    status: str = "Not Applied"
    applied_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    interview_date: Optional[datetime] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    offer_received: bool = False
    accepted: bool = False