from abc import ABC, abstractmethod
from typing import List, Optional, Pattern 
import re 
from models.job import Job

class DiscoverySource(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod 
    async def discover(self, *args, **kwargs) -> List[str]:
        ...

    
class JobExtractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def domain_patterns(self) -> List[Pattern]:
        return []

    def matches(self, url: str) -> bool:
        return any(pattern.search(url) for pattern in self.domain_patterns)


    @abstractmethod
    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        ...