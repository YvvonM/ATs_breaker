from typing import List, Optional 
import httpx 
from models.job_url import JobUrl
from sources.base import DiscoverySource

class RemotiveDiscovery(DiscoverySource):
    BASE_URL = "https://remotive.com/api/remote-jobs"

    def name(self) -> str:
        return "Remotive"

    async def discover(self, query: str, category: Optional[str], limit: int = 100, **kwargs) -> List[JobUrl]:
        params = {"search": query, "limit": limit}
        if category:
            params["category"] = category

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        discovered: List[JobUrl] = []
        for raw in data.get("jobs", []):
            job_url = raw.get("url", "")
            if not job_url:
                continue

            discovered.append(JobUrl(
                url=job_url,
                title=raw.get("title", "").strip(),
                company=raw.get("company_name", "Unknown").strip(),
                location=raw.get("candidate_required_location"),
                is_remote=True,
                source=self.name,
                raw=raw,
            ))

        return discovered