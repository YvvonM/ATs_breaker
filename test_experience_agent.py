# test_experience_agents.py

from agents.resume_rewriting.experience_parser_agent import parse_experience
from agents.resume_rewriting.experience_writer_agent import rewrite_experience

raw = """
Senior Software Engineer at Tech Corp (2020 - Present)
- Built APIs with FastAPI
- Led a team of 5

Software Engineer at Startup Inc (2017-2020)
- Wrote Python services
"""

jd = """
Senior Backend Engineer

We need a Python developer with strong FastAPI and Redis experience.
Must have 5+ years building scalable APIs.
Nice to have: Docker, Kubernetes, PostgreSQL.
"""

# Sanity check
print(f"JD length: {len(jd)}")
print(f"Experiences input: {len(raw)}")

# Test 1: Parse
print("=" * 60)
print("TEST 1: Parser")
print("=" * 60)
experiences = parse_experience(raw)
print(f"Parsed {len(experiences)} experiences")

if not experiences:
    print("❌ Parser returned nothing. Fix the parser before testing the writer.")
    exit(1)

# Test 2: Rewrite
print("\n" + "=" * 60)
print("TEST 2: Writer")
print("=" * 60)
dto = rewrite_experience(experiences, jd, ["Python", "FastAPI", "Redis"])
print(f"Status: {dto.metadata.status}")
print(f"Match score: {dto.structured.match_score}")
print(f"Keywords matched: {dto.structured.keywords_matched}")
print(f"Keywords missing: {dto.structured.keywords_missing}")
print("\nRewritten content:")
print(dto.content)