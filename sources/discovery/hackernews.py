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
    REMOTE_NEGATIONS = ["no remote", "not remote", "non-remote", "non remote"]
    REMOTE_POSITIVE_OVERRIDES = ["remote ok", "remote-ok", "remote friendly", "fully remote", "100% remote"]
    URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)

    @property
    def name(self) -> str:
        return "hackernews"

    async def discover(self, query: str, limit: int = 100, require_visa_friendly: bool = True, **kwargs) -> List[JobUrl]:
        async with httpx.AsyncClient(timeout=30) as client:
            thread = await self._find_latest_hiring_thread(client)
            if not thread:
                return []
            comments = await self._fetch_comments(client, thread, limit=limit * 3)

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
                url=url,
                title=self._extract_title(text_plain),
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

    async def _find_latest_hiring_thread(self, client: httpx.AsyncClient) -> Optional[dict]:
        url = f"{self.BASE_URL}/user/whoishiring.json"
        data = (await client.get(url)).json()

        for item_id in data.get("submitted", []):
            item = await self._fetch_item(client, item_id)
            if item and "who is hiring" in item.get("title", "").lower():
                return item
        return None

    async def _fetch_item(self, client: httpx.AsyncClient, item_id: int) -> Optional[dict]:
        url = f"{self.BASE_URL}/item/{item_id}.json"
        r = await client.get(url)
        return r.json() if r.status_code == 200 else None

    async def _fetch_comments(self, client: httpx.AsyncClient, thread: dict, limit: int) -> List[dict]:
        kids = thread.get("kids", [])[:limit]
        comments = []
        for kid_id in kids:
            c = await self._fetch_item(client, kid_id)
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
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines and '|' in lines[0]:
            parts = [p.strip() for p in lines[0].split('|')]
            if len(parts) >= 3:
                candidate = parts[2]
                # skip if it's actually a URL (some formats omit location)
                if candidate and not candidate.lower().startswith(('http://', 'https://')):
                    return candidate

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
        t = text.lower()
        if any(neg in t for neg in self.REMOTE_NEGATIONS):
            return any(p in t for p in self.REMOTE_POSITIVE_OVERRIDES)
        return any(w in t for w in ("remote", "wfh", "work from home", "anywhere", "distributed"))