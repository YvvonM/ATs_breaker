import os
from dotenv import load_dotenv
load_dotenv()

for var in [
    "GROQ_API_KEY",
    "EDUCATION_MODEL", "EXPERIENCE_MODEL", "PROJECT_MODEL", "SKILLS_MODEL", "SUMMARY_MODEL",
    "PROJECTS_MODEL", "EXPEREINCE_WRITER", "EXPERIENCE_WRITER", "EXPEREINCE_PARSER",
]:
    v = os.getenv(var)
    if v is None:
        print(f"{var:24s}: (not set)")
    else:
        kind = "GROQ KEY" if v.startswith("gsk_") else ("OPENROUTER KEY" if v.startswith("sk-or-") else "other")
        print(f"{var:24s}: {v[:10]!r}... (len={len(v)}, {kind})")
