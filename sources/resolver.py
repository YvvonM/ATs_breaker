import asyncio 
from typing import Optional 
import httpx 

class URLResolver:
    def __init__(self, timeout: float = 11.0, max_redirects: int = 10):
        self.timeout = timeout 
        self.max_redirects = max_redirects 
        self._client: Optional[httpx.AsyncClient] = None


    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout = self.timeout,
                follow_redirects = True,
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.0"
                    )
                }
            )
        return self._client

    async def resolve(self, url: str) -> str:
        client = await self._get_client()
        try:
            response = await client.head(
                url,
                follow_redirects = True
            )
            return str(response.url)
        except 

    