import time 
import json 
from typing import Any, Dict, Optional, List 
from .redis_client import redis_client

class RedisService:
    def __init__(self):
        self.client = redis_client
        self.default_ttl = 3600 

    def get_run_id(self) -> str:
        return f"run_{int(time.time())}_{id(self)}"

    def store_job_data(self, run_id:str, key:str, value:Any, ttl:Optional[int]=None) -> bool:
        redis_key = f"{run_id}:{key}"
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
                self.client.set(redis_key, value)
                if ttl or self.default_ttl:
                    self.client.expire(redis_key, ttl or self.default_ttl)
                return True
        except Exception as e:
            print(f"Error storing job data in Redis: {e}")
            
            return False

    def get_job_data(self, run_id: str, key:str) -> Optional[Any]:
        redis_key = f"resume: {run_id}:{key}"
        try:
            value = self.client.get(redis_key)
            if value:
                try: 
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        except Exception as e:
            print(f"Error retrieving job data from Redis: {e}")
        return None

    def store_agent_output(self, run_id: str, agent_name: str, output: Any) -> bool:
        return self.store_job_data(run_id, f"agent:{agent_name}", output)

    def get_agent_output(self, run_id: str, agent_name: str) -> Optional[Any]:
        return self.get_job_data(run_id, f"agent:{agent_name}")

    def set_job_status(self, run_id:str, status:str, message:Optional[str]=None) -> bool:
        data = {"status": status,} 
        if message:
                data["message"] = message
        return self.store_job_data(run_id, "status", data)

    def get_job_status(self, run_id:str) -> Optional[Dict[str, Any]]:
        return self.get_job_data(run_id, "status")

    def store_keywords(self, run_id:str, keywords: List[str]) -> bool:
        return self.store_job_data(run_id, "keywords", keywords)

    def get_keywords(self, run_id:str) -> Optional[List[str]]:
        return self.get_job_data(run_id, "keywords")

    def store_section(self, run_id:str, section_name:str, content:Any) -> bool:
        return self.store_job_data(run_id, f"section:{section_name}", content)

    def get_section(self, run_id:str, section_name:str) -> Optional[Any]:
        return self.get_job_data(run_id, f"section:{section_name}")

    def get_all_sections(self, run_id:str) -> Dict[str, Any]:
        sections = {}
        for section in ["experience", "education", "summary", "skills", "projects", "certifications"]:
            content = self.get_section(run_id, section)
            if content:
                sections[section] = content
        return sections

    def delete_job_data(self, run_id: str) -> bool:
        """Delete all data for a specific job"""
        try:
            pattern = f"resume:{run_id}:*"
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            print(f"Error deleting job data for {run_id}: {e}")
            return False

    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            return self.client.ping()
        except Exception:
            return False

redis_service = RedisService()