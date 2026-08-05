from typing import List 
import httpx 
from models.job_url import JobUrl 
from sources.base import DiscoverySource

class RemoteOKDiscovery(DiscoverySource):
    BASE_URL = "https://remoteok.com/api"

    @property
    def name(self) -> str:
        return "remoteok"

    async def discover(self, query: str, limit: int = 100, **kwargs) -> List[JobUrl]:
        async with httpx.AsyncClient(timeout = 30) as client:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
            data = response.json()


        results = data[1:] if len(data) > 1 else []
        query_lower = query.lower()
        discovered: List[JobUrl] = []
        for raw in results:
            text = f"{raw.get('position', '')} {raw.get('company', '')} {' '.join(raw.get('tags', []))}"
            if query_lower not in text.lower():
                continue

            url = raw.get("originalUrl") or raw.get("url", "")
            if not url:
                continue

            discovered.append(JobUrl(
                url=url,
                title=raw.get("position", "").strip(),
                company=raw.get("company", "Unknown").strip(),
                location=raw.get("location"),
                is_remote=True,
                source=self.name,
                raw=raw,
            ))

            if len(discovered) >= limit:
                break

        return discovered


        

