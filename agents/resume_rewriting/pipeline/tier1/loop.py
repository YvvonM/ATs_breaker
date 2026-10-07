from __future__ import annotations
import logging 
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Callable
from agents.resume_rewriting.dtos import (
     AgentName,
    RevisionStatus,
    TokenUsage,
    RevisionRecord,
    AgentRunRecord,
)
from agents.resume_rewriting.pipeline.tier1.reviewer import Tier1Reviewer
from infrastructure.db import repository

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Tier1Loop:
    def __init__(self, reviewer: Tier1Reviewer) -> None:
        self.reviewer = reviewer


    def _make_revision(
            self,
            *,
            iteration: int,
            status: RevisionStatus,
            output: Dict[str,Any],
            started_at: datetime,
            scores: Optional[Dict[str, float]] = None,
            feedback: Optional[Dict[str,List[str]]] = None,
            revision_notes: Optional[List[str]] = None,
            error: Optional[str]= None
    ):
        return RevisionRecord(
                iteration= iteration,
                status=status,
                output=output,
                scores = scores,
                feedback = feedback,
                revision_notes=revision_notes,
                started_at=started_at,
                completed_at= _utcnow(),
                error=error

            )
        

    def _persist_revision(
            self,
            *,
            run_id:str,
            agent: AgentName,
            revision: RevisionRecord

    ):
        try:
            repository.insert_revision_record(
                run_id=run_id,
                agent=agent.value,
                iteration=revision.iteration,
                status=revision.status.value,
                output=revision.output,
                scores=revision.scores,
                feedback=revision.feedback,
                revision_notes=revision.revision_notes,
                started_at=revision.started_at,
                completed_at=revision.completed_at,
                error=revision.error
            )

        except Exception:
            logger.exception(
            "Failed to persist revision run=%s agent=%s iter=%s",
            run_id, agent.value, revision.iteration,
    )

    def run(
        self,
        *,
        agent: AgentName,
        writer: Callable[..., Any],
        writer_kwargs: Dict[str, Any],
        job_description: str,
        keywords: List[str],
        run_id: str,
        max_writer_calls: int = 3,
    ) -> AgentRunRecord:
        started = _utcnow()
        revisions: List[RevisionRecord] = []
        notes: Optional[List[str]] = None
        final_output: Optional[Dict[str, Any]] = None
        final_status: RevisionStatus = RevisionStatus.FAILED
        writer_tokens = 0
        reviewer_tokens = 0
        writer_calls = 0
        reviewer_calls = 0

        if max_writer_calls <=0:
            return AgentRunRecord(
                agent=agent,
                revisions=[],
                final_output=None,
                final_status=RevisionStatus.FAILED,
                total_writer_calls=0,
                total_reviewer_calls=0,
                total_token_usage=TokenUsage(),
                started_at=started,
                completed_at=_utcnow(),
            )

        for iteration in range(max_writer_calls):
            iter_started = _utcnow()

            try:
                writer_output = writer(
                    **writer_kwargs,
                    run_id=run_id,
                    revision_notes=notes,
                )
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.warning(
                    "Tier1 writer failed for agent=%s run=%s iter=%d: %s",
                    agent.value, run_id, iteration, error_msg,
                )

                rev = self._make_revision(
                    iteration = iteration,
                    status= RevisionStatus.WRITER_FAILED,
                    output=final_output or {},
                    started_at=iter_started,
                    error=error_msg,
                )
                revisions.append(rev)
                self._persist_revision(run_id=run_id, agent=agent, revision=rev)
                final_status = RevisionStatus.WRITER_FAILED
                break

            writer_calls += 1
            writer_tokens += writer_output.metadata.token_count
            final_output = writer_output.model_dump(mode="json")

            if iteration == max_writer_calls - 1:
                rev = self._make_revision(
                    status=RevisionStatus.MAX_ITERATIONS,
                    iteration=iteration,
                    output=final_output,
                    started_at=iter_started,
                )
                revisions.append(rev)
                self._persist_revision(run_id=run_id, agent=agent, revision = rev)
                final_status = RevisionStatus.MAX_ITERATIONS
                break

            review = self.reviewer.review(
                agent = agent.value,
                section_content = writer_output.content,
                section_structured = writer_output.structured.model_dump(mode="json"),
                job_description = job_description,
                keywords = keywords,
                run_id = run_id,
            )
            reviewer_calls += 1
            reviewer_tokens = review.token_count
            if review.error:
                rev = self._make_revision(
                    iteration=iteration,
                    status=RevisionStatus.REVIEWER_FAILED,
                    output=final_output,
                    started_at=iter_started,
                    error=review.error,
                )
                revisions.append(rev)
                self._persist_revision(run_id=run_id, agent=agent, revision=rev)
                final_status = RevisionStatus.REVIEWER_FAILED
                break

            if review.decision == "accept":
                rev = self._make_revision(
                    iteration=iteration,
                    status=RevisionStatus.ACCEPTED,
                    output=final_output,
                    started_at=iter_started,
                    scores=review.scores,
                    feedback=review.feedback,
                    revision_notes=review.revision_notes,
                )
                revisions.append(rev)
                self._persist_revision(run_id=run_id, agent=agent, revision=rev)
                final_status = RevisionStatus.ACCEPTED
                break

            rev = self._make_revision(
                iteration=iteration,
                status=RevisionStatus.RETRY,
                output=final_output,
                started_at=iter_started,
                scores=review.scores,
                feedback=review.feedback,
                revision_notes=review.revision_notes,
            )
            revisions.append(rev)
            self._persist_revision(run_id=run_id, agent=agent, revision=rev)
            notes = review.revision_notes
            final_status = RevisionStatus.RETRY


        return AgentRunRecord(
            agent=agent,
            revisions=revisions,
            final_output=final_output,
            final_status=final_status,
            total_writer_calls=writer_calls,
            total_reviewer_calls=reviewer_calls,
            total_token_usage=TokenUsage(
                input_tokens=writer_tokens + reviewer_tokens,
                output_tokens=0,
            ),
            started_at=started,
            completed_at=_utcnow(),
        )

            





            
