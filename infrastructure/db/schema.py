from datetime import datetime, timezone
from typing import  Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text, Index

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class LLMResponseCache(SQLModel, table = True):
    __tablename__ = "llm_response_cache"
    __table_args__ = (
        Index("ix_cache_agent_role", "agent", "role"),
    )

    cache_key: str = Field(
        primary_key=True,
        description="sha256 of prompt_version|agent|role|model|temperature|prompt_hash",
    )
    prompt_version: str = Field(
        index=True,
        description="Version string of the prompt template. Bump to invalidate.",
    )
    agent: str = Field(index=True, description="Agent name (e.g. 'experience').")
    role: str = Field(index=True, description="'writer' | 'reviewer' | 'editor'.")
    model: str = Field(index=True, description="LLM model name.")
    temperature: float = Field(description="Sampling temperature used.")
    prompt_hash: str = Field(index=True, description="sha256 of the full prompt text.")

    response_json: str = Field(
        sa_column=Column(Text),
        description="The LLM's raw JSON response.",
    )
    input_tokens: int = Field(default=0, description="Prompt tokens.")
    output_tokens: int = Field(default=0, description="Completion tokens.")

    hit_count: int = Field(default=0, description="How many times this entry was served.")
    last_hit_at: Optional[datetime] = Field(default=None, description="Last cache hit time.")
    created_at: datetime = Field(default_factory=_utcnow, index=True)


class RevisionRecordRow(SQLModel, table=True):
    __tablename__ = "revision_record"
    __table_args__ = (
        Index("ix_revision_run_agent", "run_id", "agent"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: str = Field(
        index=True,
        foreign_key="cv_generation.run_id",
        description="Links to the CV generation run.",
    )
    agent: str = Field(index=True, description="Agent name.")
    iteration: int = Field(description="0 = first draft, 1+ = corrections.")
    status: str = Field(
        index=True,
        description="RevisionStatus value (accepted, retry, etc.).",
    )
    output_json: str = Field(
        sa_column=Column(Text),
        description="The draft output, serialized as JSON.",
    )
    scores_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Reviewer scores, serialized JSON.",
    )
    feedback_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Reviewer feedback, serialized JSON.",
    )
    revision_notes_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Notes to feed back into the next iteration.",
    )

    started_at: datetime = Field(description="When this iteration started.")
    completed_at: Optional[datetime] = Field(default=None, description="When it finished.")
    error: Optional[str] = Field(default=None, description="Error message if failed.")

class LLMCallRecordRow(SQLModel, table=True):
    __tablename__ = "llm_call_record"
    __table_args__ = (
        Index("ix_llm_call_run_role", "run_id", "role"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: str = Field(
        index=True,
        foreign_key="cv_generation.run_id",
        description="Links to the CV generation run.",
    )
    agent: str = Field(index=True, description="Agent name.")
    role: str = Field(index=True, description="'writer' | 'reviewer' | 'editor'.")
    model: str = Field(description="LLM model name.")
    temperature: float = Field(description="Sampling temperature.")

    prompt_hash: str = Field(index=True, description="sha256 of the prompt.")
    response_hash: str = Field(description="sha256 of the response.")

    cached: bool = Field(
        index=True,
        description="True if served from cache, False if live call.",
    )
    input_tokens: int = Field(default=0, description="Prompt tokens.")
    output_tokens: int = Field(default=0, description="Completion tokens.")

    latency_seconds: float = Field(description="Wall-clock duration of the call.")
    started_at: datetime = Field(description="Call start time.")
    completed_at: datetime = Field(description="Call end time.")
    error: Optional[str] = Field(default=None, description="Error message if failed.")


