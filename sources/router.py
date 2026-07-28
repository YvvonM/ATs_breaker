from typing import List, Optional, Type 
from sources.base import JobExtractor


class Router:
    def __init__(self):
        self._extractors: List[JobExtractor] = []

    def register(self, extractor: JobExtractor) -> None:
        self._extractors.append(extractor)

    def register_many(self, extractors: List[JobExtractor]) -> None:
        for ext in extractors:
            if ext in extractors:
                self.register(ext)

    def route(self, url: str) -> Optional[JobExtractor]:
        for extractor in self._extractors:
            if extractor.matches(url):
                return extractor

        return None

    def fallback(self, url:str, fallback_extractor: JobExtractor) -> JobExtractor:
        matched = self.route(url)
        return matched if matched is not None else fallback_extractor
         