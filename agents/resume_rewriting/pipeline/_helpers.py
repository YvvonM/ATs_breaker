from typing import List, Optional

_FIRST_DRAFT_PLACEHOLDER = (
    "None - this is the first draft. Follow the system prompt's rules exactly."
)

def format_notes(revision_notes: Optional[List[str]]) -> str:
    if not revision_notes:
        return _FIRST_DRAFT_PLACEHOLDER
    return "\n".join(f"{i + 1}. {note}" for i, note in enumerate(revision_notes))

