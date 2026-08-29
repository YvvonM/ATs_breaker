import html 
import json 
from typing import Optional, List 
import re 
import httpx 
from models.job_url import JobUrl
from sources.base import DiscoverySource

class YCJobsDiscovery(DiscoverySource):
    BASE_URL = "https://www.workatastartup.com/jobs"
    VISA_FRIENDLY = {
    "united states", "usa", "us", "remote", "worldwide",
    "canada", "united kingdom", "uk", "gb", "england", "germany", "netherlands",
    "ireland", "singapore", "australia", "sweden", "switzerland",
    "france", "spain", "portugal", "estonia", "lithuania", "dubai", "uae",
    }


    @property
    def name(self) -> str:
        return "yc_jobs"

        
    async def discover(self, query:str, role_type: Optional[str] = None, limit: int = 100, visa_friendly_only: bool = False, **kwargs,) -> List[JobUrl]:
        async with httpx.AsyncClient(timeout = 30.0) as client:
            response = await client.get(
                self.BASE_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            response.raise_for_status()


        raw_jobs = self._extract_jobs(response.text)
        query_lower = query.lower()
        discovered: List[JobUrl] = []
        for raw in raw_jobs:
            search_blob = json.dumps(raw).lower()
            if query_lower not in search_blob:
                continue
            if role_type and role_type.lower() not in raw.get("roleType", "").lower():
                continue
            job = self._parse_result(raw)
            if visa_friendly_only and not self._is_visa_friendly(job):
                continue
            discovered.append(job)
            if len(discovered) >= limit:
                break

        return discovered

    def _extract_jobs(self, html_text: str) -> List[dict]:
        match = re.search(r'"jobs"\s*:\s*(\[.*?\])\s*,\s*"total"', html_text, re.DOTALL)
        if not match:
            return []

        try:
            jobs = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError:
            return []

        if not isinstance(jobs, list):
            return []

        return jobs
    def _parse_result(self, raw: dict) -> JobUrl:
        job_id = raw['id']
        location = raw.get('location','')
        return JobUrl(
            url = f"https://www.workatastartup.com/jobs/{job_id}",
            title = raw.get("title", "").strip(),
            company=raw.get("companyName", "Unknown").strip(),
            location=location,
            is_remote="remote" in location.lower(),
            source=self.name,
            raw=raw,
        )


    def _is_visa_friendly(self, job: JobUrl) -> bool:
        if not job.location:
            return False
        loc_lower = job.location.lower()
        return any(v in loc_lower for v in self.VISA_FRIENDLY)



