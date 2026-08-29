import os 
from typing import List, Any, Optional 
import httpx 
from models.job import Job 
from sources.base import JobExtractor
from models.firecrawl_model import FirecrawlJobSchema
import asyncio
from dotenv import load_dotenv
load_dotenv()

class FireCrawlExtractor(JobExtractor):
    BASE_URL = "https://api.firecrawl.dev/v2/extract"
    POLL_INTERVAL_SECONDS = 3
    MAX_POLL_ATTEMPTS = 40 

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FirecrawlExtractor requires FIRECRAWL_API_KEY")

    @property
    def name(self) -> str:
        return "firecrawl"


    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        payload = {
            "urls": [url],
            "schema": FirecrawlJobSchema.model_json_schema(),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout = 90) as client:
            start_response = await client.post(self.BASE_URL, headers=headers, json=payload)
            start_response.raise_for_status()
            start_data = start_response.json()
            if not start_data.get("success"):
                raise RuntimeError(f"Firecrawl extract failed to start: {start_data}")

            job_id = start_data["id"]
            status_url = f"{self.BASE_URL}/{job_id}"
            for _ in range(self.MAX_POLL_ATTEMPTS):
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                status_response = await client.get(status_url, headers=headers)
                status_response.raise_for_status()
                status_data = status_response.json()
                status = status_data.get("status")
                if status == "completed":
                    result = status_data.get("data", {})
                    break
                if status in ("failed", "cancelled"):
                    raise RuntimeError(f"Firecrawl extract job {job_id} ended with status={status}")
            else:
                raise TimeoutError(f"Firecrawl extract job {job_id} did not complete in time")


        parsed = FirecrawlJobSchema.model_validate(result)
        return Job(
            source=self.name,
            url=url,
            company=parsed.company,
            title=parsed.title,
            location=parsed.location,
            is_remote=parsed.is_remote,
            employment_type=parsed.employment_type,
            seniority=parsed.seniority,
            description=parsed.description,
            requirements=parsed.requirements or [],
            salary_min=parsed.salary_min,
            salary_max=parsed.salary_max,
            visa_sponsorship=parsed.visa_sponsorship,
        )

