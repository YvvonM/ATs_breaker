import re 
from typing import List, Optional 
import httpx 
from models.job_url import JobUrl
from sources.base import DiscoverySource

class HackerNewsDiscovery(DiscoverySource):
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    VISA_SIGNALS = [
        "visa", "sponsorship", "sponsor", "h1b", "h-1b", "relocation",
        "relocate", "work permit", "work visa", "immigration", "green card",
        "relocation assistance", "will sponsor", "can sponsor", "visa transfer",
    ]
    URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)

    @property
    def name(self) -> str:
        return "Hacker News"

    async def discover(self, query: str, limit :int = 100, require_visa_friendly: bool = True, **kwargs) -> List[JobUrl]:
        thread_id = await self._find_latest_hiring_thread()
        if not thread_id:
            return []

        comments = await self._fetch_comments(thread_id, limit = limit * 3)
        query_lower = query.lower()
        discovered: List[JobUrl] = []
        for comment in comments:
            text = comment.get("text", "")
            if not text or query_lower not in text.lower():
                continue

            text_plain = self._strip_html(text)
            is_visa = self._mentions_visa(text_plain)
            is_remote = self._mentions_remote(text_plain)

            if require_visa_friendly and not (is_visa or is_remote):
                continue

            urls = self.URL_RE.findall(text_plain)
            url = urls[0] if urls else f"https://news.ycombinator.com/item?id={comment['id']}"
            discovered.append(JobUrl(
                url = url,
                title = self._extract_title(text_plain),
                company=self._extract_company(text_plain),
                location=self._extract_location(text_plain),
                is_remote=is_remote,
                source=self.name,
                raw={
                    "hn_id": comment.get("id"),
                    "by": comment.get("by"),
                    "text": text_plain,
                    "visa_sponsorship": is_visa,
                },
            ))

            if len(discovered) >= limit:
                break 

        return discovered

    async def _find_latest_hiring_thread(self) -> Optional[int]:
        url = f"{self.BASE_URL}/user/whoishiring.json"
        async with httpx.AsyncClient(timeout = 30) as client:
            data = (await client.get(url)).json()

        for item_id in data.get("submitted", []):
            item = await self._fetch_item(item_id)
            if item and "who is hiring" in item.get("title", "").lower():
                return item_id
        return None

        
    async def _fetch_item(self, item_id: int) -> Optional[dict]:
        url = f"{self.BASE_URL}/item/{item_id}.json"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            return r.json() if r.status_code == 200 else None

    async def _fetch_comments(self, thread_id: int, limit: int) -> List[dict]:
        thread = await self._fetch_item(thread_id)
        if not thread:
            return []
        kids = thread.get("kids", [])[:limit]
        comments = []
        for kid_id in kids:
            c = await self._fetch_item(kid_id)
            if c and not c.get("deleted") and not c.get("dead"):
                comments.append(c)
        return comments

    def _strip_html(self, text: str) -> str:
        text = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>[^<]*</a>', r'\1', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _extract_company(self, text: str) -> str:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return "Unknown"
        first = lines[0]
        if '|' in first:
            return first.split('|')[0].strip()
        return first if len(first) < 50 and first[0].isupper() else "Unknown"

    def _extract_title(self, text: str) -> str:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return "Unknown"
        first = lines[0]
        if '|' in first:
            parts = [p.strip() for p in first.split('|')]
            return parts[1] if len(parts) >= 2 else parts[0]
        return "Software Engineer"

    def _extract_location(self, text: str) -> Optional[str]:
        for pattern in [
            r'[Ll]ocation[:;]\s*([^\n]+)',
            r'[Bb]ased in[:;]\s*([^\n]+)',
        ]:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
        if re.search(r'\bRemote\b', text):
            return "Remote"
        return None

    def _mentions_visa(self, text: str) -> bool:
        return any(s in text.lower() for s in self.VISA_SIGNALS)

    def _mentions_remote(self, text: str) -> bool:
        return any(w in text.lower() for w in ("remote", "wfh", "work from home", "anywhere", "distributed"))



