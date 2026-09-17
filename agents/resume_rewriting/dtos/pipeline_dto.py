from __future__ import annotations
from datetime import datetime
from enum import Enum 
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from .common_dto import AgentName, RevisionStatus, PipelineStatus, TokenUsage

class PipelineConfig(BaseModel):
    max_writer_calls_per_agent: int = 3
    max_tier2_iterations: int = 2
    max_workers: int = 3
    token_budget: int = 500_000
    response_cache_ttl_seconds: int = 7 * 24 * 60 * 60
    temperature_writer: float = 0.5
    temperature_reviewer: float = 0.1
    temperature_editor: float = 0.4
    model_writer: str = ""
    model_reviewer: str = ""
    model_editor: str = ""
    skip_editor_on_excellent: bool = True


class LLMCallRecord(BaseModel):
    agent: AgentName
    role: Literal["writer", "reviewer", "editor"]
    model: str
    temperature: float
    prompt_hash: str
    response_hash: str
    cached: bool
    token_usage: TokenUsage
    latency_seconds: float
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None

class RevisionRecord(BaseModel):
    iteration: int
    status: RevisionStatus
    output: Dict[str, Any]
    scores: Optional[Dict[str, float]] = None
    feedback: Optional[Dict[str, List[str]]] = None
    revision_notes: Optional[List[str]] = None
    llm_calls: List[LLMCallRecord] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class AgentRunRecord(BaseModel):
    agent: AgentName
    revisions: List[RevisionRecord] = Field(default_factory=list)
    final_output: Optional[Dict[str, Any]] = None
    final_status: RevisionStatus
    total_writer_calls: int = 0
    total_reviewer_calls: int = 0
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)
    started_at: datetime
    completed_at: Optional[datetime] = None

class StageRecord(BaseModel):
    stage: Literal["tier1", "assembly", "tier2_review", "tier2_edit"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    error: Optional[str] = None

class PipelineRecord(BaseModel):
    run_id: str
    config: PipelineConfig
    status: PipelineStatus
    agents: Dict[str, AgentRunRecord] = Field(default_factory=dict)
    stages: List[StageRecord] = Field(default_factory=list)
    manager_output: Optional[Dict[str, Any]] = None
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)
    token_budget_remaining: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

def has_budget_for_retry(
    agent_record: AgentRunRecord,
    config: PipelineConfig,
    pipeline_tokens_used: int,
) -> bool:
    if agent_record.total_writer_calls >= config.max_writer_calls_per_agent:
        return False
    if pipeline_tokens_used >= config.token_budget:
        return False
    return True