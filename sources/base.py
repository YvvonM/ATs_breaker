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
    async def discovery(self, *args, *kwargs) -> List[str]:
        ...

    
class JobExtractor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def domain_patterns(self) -> List[Pattern]:
        return []

    @abstractmethod
    async def extract(self, url: str, html: Optional[str] = None) -> Job:
        ...