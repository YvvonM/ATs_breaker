# ATS Breaker

Assist in job application by helping resumes and application materials match job descriptions and pass Applicant Tracking Systems (ATS).

## Key features

- Parse job descriptions and resumes to extract keywords and required skills
- Score how well a resume matches a job description and highlight gaps
- Suggest targeted edits, bullets, and phrasing to improve match rate
- Generate tailored cover letter drafts and resume summaries
- Export a tailored resume or checklist for human review

## Why use this

ATS Breaker helps reduce the manual effort of tailoring applications and increases the chance your application will be noticed by recruiters and ATS software. It is intended as a developer-friendly toolkit for building automation and assistance around job applications.

## Installation

1. Create a virtual environment and activate it:
   - python -m venv venv
   - source venv/bin/activate   (Linux / macOS)
   - venv\Scripts\activate      (Windows)

2. Install dependencies:
   - pip install -r requirements.txt

If there is no requirements.txt yet, install the packages your project needs or run:
- pip install -e .

## Quick start

Example command-line usage (replace with your actual entry point or script):

- Analyze a job description and resume:
  - python tools/analyze.py --resume path/to/resume.pdf --job path/to/job.txt --out report.json

Example library usage (illustrative, adjust to your API):

```python
from ats_breaker import ATSBreaker

breaker = ATSBreaker()
result = breaker.tailor_resume(resume_path="resume.pdf", job_path="job_description.txt")
print("Match score:", result.get("score"))
print("Suggested edits:", result.get("suggestions")[:5])
