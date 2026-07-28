AI_KEYWORDS = {
    "ai", "ml", "machine learning", "deep learning", "llm", "large language model",
    "nlp", "natural language processing", "computer vision", "cv",
    "mle", "machine learning engineer", "ai engineer", "ml engineer",
    "research engineer", "applied scientist", "data scientist",
    "pytorch", "tensorflow", "jax", "transformers", "hugging face",
    "openai", "anthropic", "foundation model", "generative ai", "genai",
    "reinforcement learning", "rlhf", "fine-tuning", "inference",
    "vector database", "embedding", "rag", "retrieval augmented",
}

EXTRACTION_PROMPT = """You are parsing a job post from Hacker News "Who is Hiring".
Extract the following fields from the text. If a field is not mentioned, use null.

Return ONLY a JSON object with this exact structure:
{{
  "company": "Company name, or null if unclear",
  "role_title": "The specific job title, or best guess",
  "location": "Office location, or 'Remote', or 'Global', or null",
  "is_remote": true/false,
  "remote_restrictions": "Any geographic restrictions mentioned (e.g., 'US only'), or null",
  "visa_sponsorship": true/false/null,
  "tech_stack": ["list", "of", "technologies", "mentioned"],
  "experience_required": "Years or level mentioned, or null",
  "salary_range": "Salary or comp mentioned, or null",
  "apply_method": "URL, email, or instructions to apply",
  "description_summary": "2-3 sentence summary of what the role involves"
}}

Job post text:
---
{text}
---

Return valid JSON only. No markdown, no explanations."""

