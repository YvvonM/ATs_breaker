import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .redis_client import redis_client

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime by converting to ISO strings."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RedisService:
    """Ephemeral pipeline state.

    Redis is used ONLY for:
      - Live run status / progress (TTL-bound)
      - Progress event streams (for SSE)
      - Short-lived locks (chain build, rate limiting)

    Durable data (agent outputs, sections, keywords, revisions, LLM cache)
    lives in Neon, not here.

    The ``store_*``/``get_*`` methods for sections/keywords/agent outputs are
    DEPRECATED shims kept for backwards compatibility. They will be removed
    once all callers migrate to the Neon repository.
    """

    def __init__(self):
        self.client = redis_client
        self.default_ttl = 3600  # 1 hour

    def _key(self, run_id: str, key: str) -> str:
        """Single source of truth for Redis key format."""
        return f"resume:{run_id}:{key}"

    def get_run_id(self) -> str:
        """Generate a collision-safe run id."""
        return f"run_{uuid.uuid4().hex}"


    def store_job_data(
        self,
        run_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store a value with a TTL. Every write has an expiry."""
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        if ttl_seconds <= 0:
            logger.warning(
                "store_job_data called with non-positive TTL=%s", ttl_seconds
            )
            return False

        try:
            serialized = json.dumps(value, cls=DateTimeEncoder)
        except (TypeError, ValueError):
            logger.exception("Cannot serialize value for key %s", key)
            return False

        redis_key = self._key(run_id, key)
        try:
            self.client.setex(redis_key, ttl_seconds, serialized)
        except Exception:
            logger.exception("Redis SETEX failed for key %s", redis_key)
            return False
        return True

    def get_job_data(self, run_id: str, key: str) -> Optional[Any]:
        """Read a value. Returns None on missing key or Redis error."""
        redis_key = self._key(run_id, key)
        try:
            value = self.client.get(redis_key)
        except Exception:
            logger.exception("Redis GET failed for key %s", redis_key)
            return None

        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Value wasn't JSON (shouldn't happen with our writer, but be safe)
            return value

    def set_job_status(
        self, run_id: str, status: str, message: Optional[str] = None
    ) -> bool:
        data: Dict[str, Any] = {"status": status}
        if message:
            data["message"] = message
        return self.store_job_data(run_id, "status", data)

    def get_job_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.get_job_data(run_id, "status")

    def set_progress(
        self,
        run_id: str,
        completed: int,
        total: int,
        stage: str,
        message: Optional[str] = None,
    ) -> bool:
        data: Dict[str, Any] = {
            "completed_agents": completed,
            "total_agents": total,
            "stage": stage,
        }
        if message:
            data["message"] = message
        return self.store_job_data(run_id, "progress", data)

    def get_progress(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.get_job_data(run_id, "progress")


    def emit_event(
        self, run_id: str, event_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Append an event to the run's stream. Best-effort."""
        try:
            stream_key = self._key(run_id, "events")
            fields = {
                "type": event_type,
                "payload": json.dumps(payload, cls=DateTimeEncoder),
                "ts": datetime.utcnow().isoformat(),
            }
            self.client.xadd(stream_key, fields, maxlen=1000, approximate=True)
            # Expire the stream so it doesn't live forever.
            self.client.expire(stream_key, self.default_ttl)
            return True
        except Exception:
            logger.exception(
                "Failed to emit event %s for run %s", event_type, run_id
            )
            return False

    def read_events(
        self,
        run_id: str,
        last_id: str = "$",
        block_ms: int = 5000,
        count: int = 100,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Blocking read from the run's stream.

        Returns a list of ``(event_id, fields)`` tuples.
        """
        stream_key = self._key(run_id, "events")
        try:
            result = self.client.xread(
                {stream_key: last_id},
                block=block_ms,
                count=count,
            )
        except Exception:
            logger.exception("Failed to read events for run %s", run_id)
            return []

        events: List[Tuple[str, Dict[str, Any]]] = []
        for _stream_name, entries in result or []:
            for entry_id, fields in entries:
                payload_raw = fields.get("payload", "{}")
                try:
                    payload = json.loads(payload_raw)
                except (json.JSONDecodeError, TypeError):
                    payload = {"raw": payload_raw}
                events.append(
                    (
                        entry_id,
                        {
                            "type": fields.get("type", ""),
                            "payload": payload,
                            "ts": fields.get("ts", ""),
                        },
                    )
                )
        return events

    def delete_job_data(self, run_id: str) -> bool:
        """Delete all keys under a run_id."""
        try:
            pattern = self._key(run_id, "*")
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                # Chunk deletes to stay under Redis arg limits.
                for i in range(0, len(keys), 500):
                    self.client.delete(*keys[i : i + 500])
            return True
        except Exception:
            logger.exception("Error deleting job data for run %s", run_id)
            return False

    def health_check(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:
            logger.exception("Redis health check failed")
            return False

   #depreciated
   
    def store_agent_output(
        self, run_id: str, agent_name: str, output: Any
    ) -> bool:
        logger.warning(
            "store_agent_output is deprecated; persist to Neon instead"
        )
        return self.store_job_data(run_id, f"agent:{agent_name}", output)

    def get_agent_output(
        self, run_id: str, agent_name: str
    ) -> Optional[Any]:
        logger.warning(
            "get_agent_output is deprecated; read from Neon instead"
        )
        return self.get_job_data(run_id, f"agent:{agent_name}")

    def store_keywords(self, run_id: str, keywords: List[str]) -> bool:
        logger.warning(
            "store_keywords is deprecated; persist to Neon instead"
        )
        return self.store_job_data(run_id, "keywords", keywords)

    def get_keywords(self, run_id: str) -> Optional[List[str]]:
        logger.warning(
            "get_keywords is deprecated; read from Neon instead"
        )
        return self.get_job_data(run_id, "keywords")

    def store_section(
        self, run_id: str, section_name: str, content: Any
    ) -> bool:
        logger.warning(
            "store_section is deprecated; persist to Neon instead"
        )
        return self.store_job_data(run_id, f"section:{section_name}", content)

    def get_section(
        self, run_id: str, section_name: str
    ) -> Optional[Any]:
        logger.warning(
            "get_section is deprecated; read from Neon instead"
        )
        return self.get_job_data(run_id, f"section:{section_name}")

    def get_all_sections(self, run_id: str) -> Dict[str, Any]:
        logger.warning(
            "get_all_sections is deprecated; read from Neon instead"
        )
        sections: Dict[str, Any] = {}
        for section in [
            "experience",
            "education",
            "summary",
            "skills",
            "projects",
        ]:
            content = self.get_section(run_id, section)
            if content:
                sections[section] = content
        return sections


redis_service = RedisService()