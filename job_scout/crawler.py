import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode



@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: Optional[int]
    html: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code == 200

class RateLimiter:
    def __init__(self, default_delay: float = 1.2):
        self.default_delay = default_delay
        self._last_request: Dict[str, float] = defaultdict(float)
        self._domain_delays: Dict[str, float] = {}

    def set_domain_delay(self, domain: str, delay: float):
        self._domain_delays[domain] = delay

    async def wait(self, url: str):
        domain = urlparse(url).netloc
        delay = self._domain_delays.get(domain, self.default_delay)
        last = self._last_request[domain]
        elapsed = time.monotonic() - last
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request[domain] = time.monotonic()



class Crawler:
    def __init__(self, timeout: int = 30, max_retries: int = 3, base_delay: float = 1.0,
        rate_limit_delay: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._crawler: Optional[AsyncWebCrawler] = None
        self._rate_limiter = RateLimiter(default_delay=rate_limit_delay)

    async def __aenter__(self):
        self._crawler = AsyncWebCrawler()
        await self._crawler.__aenter__()
        return self


    async def __aexit__(self,exc_type, exc_val, exc_tb):
        if self._crawler:
            await self._crawler.__aexit__(exc_type, exc_val, exc_tb)

    def set_domain_rate(self, domain: str, delay: float):
        self._rate_limiter.set_domain_delay(domain, delay)


    async def _retry(self, operation, url: str) -> FetchResult:
        for attempt in range(1, self.max_retries + 1):
            await self._rate_limiter.wait(url)

            result = await operation()

            if result.ok:
                return result

        
            if result.status_code and 400 <= result.status_code < 500:
                return result

            if attempt < self.max_retries:
                sleep = self.base_delay * (2 ** (attempt - 1))
                await asyncio.sleep(sleep)

        return result 

    
    async def fetch_html(self, url:str, headers: Optional[Dict[str, str]] = None, wait_for: Optional[str] = None) -> FetchResult:
        async def _do_fetch() -> FetchResult:
            if not self._crawler:
                raise RuntimeError("Crawler not started. Use 'async with' context.")
            
            config = CrawlerRunConfig(
                cache_mode = CacheMode.BYPASS,
                wait_for=wait_for,
                page_timeout=self.timeout * 1000,
            )

            try:
                result = await self._crawler.arun(url = url, config = config)
                return FetchResult(
                        url=url,
                        status_code=result.status_code,
                        html=result.html,
                    )

            except Exception as e:
                return FetchResult(
                        url=url,
                        status_code=None,
                        error=str(e),
                    )

        return await self._retry(_do_fetch, url)

    async def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None,) -> FetchResult:
        async def _do_fetch() -> FetchResult:
            try:
                async with httpx.AsyncClient(timeout = self.timeout) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if data is None:
                        return FetchResult(
                            url=url,
                            status_code=response.status_code,
                            error="Response body is null",
                        )
                    return FetchResult(
                        url=url,
                        status_code=response.status_code,
                        json_data=response.json(),
                    )

            except Exception as e:
                return FetchResult(
                    url=url,
                    status_code=getattr(e, "response", None) and e.response.status_code,
                    error=str(e),
                )
        return await self._retry(_do_fetch, url)
 

        
