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
                max_redirects=self.max_redirects,
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "identity",  
                }
            )
        return self._client

    async def resolve(self, url: str) -> str:
        client = await self._get_client()
        response = await self._try_head_then_get(client, url)
        final = str(response.url)
        return self._clean_url(final)

    async def _try_head_then_get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        try:
            response = await client.head(url, allow_redirects=True)
            if response.status_code < 400:
                return response
        except (httpx.RequestError, httpx.HTTPStatusError):
            if getattr(e, "response", None) and e.response.status_code == 405:
                pass

            else:
                raise 

        return await client.get(url)

    def _clean_url(self, url: str) -> str:
        if "?" not in url:
            return url

        base, query = url.split("?", 1)
        if not query:
            return base

        kept = []
        for param in query.split("&"):
            if not param:
                continue
            key = param.split("=")[0].lower()
            if key not in self.TRACKING_PARAMS:
                kept.append(param)

        if not kept:
            return base
        return f"{base}?{'&'.join(kept)}"


    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()







    