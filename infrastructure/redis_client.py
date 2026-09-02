import os 
import redis 
from dotenv import load_dotenv
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL not set in environment variables")

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses= True,
    socket_timeout = 100,
    socket_connect_timeout=100,
)

rq_redis_connection = redis.from_url(
    REDIS_URL,
    decode_responses=False,  
)
def ping_redis():
    """Test Redis connection"""
    try:
        return redis_client.ping()
    except Exception as e:
        return f"Error: {e}"