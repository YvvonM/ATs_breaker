import re 
from typing import Optional 
import httpx 
from bs4 import BeautifulSoup 
from model.job import Job 
from sources.base import JobExtractor

class AshbyExtractor(JobExtractor):
    @property
    def name(self) -> str:
        return "Ashby"

    @property
    def domain_patters(self):
        return [
            re.compile(r"jobs\.ashbyhq\.com", re.I),
        ]

    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        api_job = await self._try_api(url)
        if api_job:
            return api_job 

        if html is None:
            html = await self._fetch(url)
        return self._extract_from_html(url, html)

    async def _try_api(self, url:str) -> Optional[Job]:
        parsed = self._parse_url(url)
        if not parsed:
            return None 

        company, job_id = parsed
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                data = response.json()

            job = next(
                (j for j in data.get("jobs", []) if j.get("id") == job_id),
                None
            )
            if job:
                return self._build_from_api(url, job)

        except (httpx.HTTPError)

