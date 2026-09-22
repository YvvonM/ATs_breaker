"""One-off script: add composite indexes missing from the initial create_all.

The composite Index(...) declarations at the bottom of schema.py weren't
picked up by SQLModel.metadata.create_all on the first run, so we add them
here. IF NOT EXISTS makes this idempotent — safe to run multiple times.
"""

from infrastructure.db.sync_engine import sync_session
from sqlalchemy import text

INDEXES = [
    (
        "ix_llm_call_run_role",
        "CREATE INDEX IF NOT EXISTS ix_llm_call_run_role "
        "ON llm_call_record (run_id, role)",
    ),
    (
        "ix_revision_run_agent",
        "CREATE INDEX IF NOT EXISTS ix_revision_run_agent "
        "ON revision_record (run_id, agent)",
    ),
    (
        "ix_cache_agent_role",
        "CREATE INDEX IF NOT EXISTS ix_cache_agent_role "
        "ON llm_response_cache (agent, role)",
    ),
]


def main() -> None:
    with sync_session() as s:
        for name, ddl in INDEXES:
            print(f"Creating {name} ...")
            s.execute(text(ddl))
    print("Done.")


if __name__ == "__main__":
    main()