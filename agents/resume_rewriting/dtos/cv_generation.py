from datetime import datetime 
from typing import List, Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, Text, JSON

class CVGeneration(SQLModel, table = True):
    __tablename__ = "cv_generation"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    application_id: str = Field(foreign_key="application.id", index = True)
    run_id: str = Field(index=True, unique=True, description="Unique identifier for the CV generation run")
    job_description: str = Field(sa_column=Column(Text), description="Job description text")
    master_cv: str = Field(sa_column=Column(Text), description="Master CV text")
    agent_outputs: Optional[str] = Field(default = None, sa_column=Column(JSON), description="Aggregated outputs from all agents as JSON string")
    extracted_keywords: Optional[List[str]] = Field(default = None, sa_column=Column(JSON), description="Extracted keywords from the job description")
    keyword_count: Optional[int] = Field(default = 0, description="Count of extracted keywords")
    experience_section: Optional[str] = Field(default = None, sa_column=Column(Text), description="Generated experience section")
    education_section: Optional[str] = Field(default = None, sa_column=Column(Text), description="Generated education section")
    summary_section: Optional[str] = Field(default = None, sa_column=Column(Text), description="Generated summary section")
    skills_section: Optional[str] = Field(default = None, sa_column=Column(Text), description="Generated skills section")
    model_used: Optional[str] = Field(default = None, description="Model used for CV generation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the CV generationwas created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the CV generation was last updated")
    completed_at: Optional[datetime] = Field(default = None, description="Timestamp when the CV generation was completed")
