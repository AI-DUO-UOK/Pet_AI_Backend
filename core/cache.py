import os
import logging
import json
from typing import Optional, Any
from interfaces.cache_service import ICacheService

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    has_redis = True
except ImportError:
    has_redis = False

class CacheService(ICacheService):
    """Caching service with Redis backend and in-memory fallback"""
    
    def __init__(self):
        self.redis_client = None
        self.in_memory_cache = {}
        self.in_memory_expires = {}
        
        if has_redis:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                    # Test connection
                    self.redis_client.ping()
                    logger.info("Connected to Redis server successfully")
                except Exception as e:
                    logger.warning(f"Failed to connect to Redis at {redis_url}: {e}. Falling back to in-memory cache.")
                    self.redis_client = None
            else:
                logger.info("REDIS_URL not set. Using in-memory cache.")
        else:
            logger.info("redis package not installed. Using in-memory cache.")
            
    def get(self, key: str) -> Optional[Any]:
        """Retrieve key from cache"""
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.warning(f"Redis get failed for {key}: {e}")
            return None
        
        # In-memory fallback
        import time
        if key in self.in_memory_cache:
            expire_at = self.in_memory_expires.get(key, 0)
            if expire_at == 0 or expire_at > time.time():
                return self.in_memory_cache[key]
            # Expired
            self.delete(key)
        return None

    def set(self, key: str, value: Any, expire_seconds: int = 3600):
        """Set key in cache with expiry"""
        if self.redis_client:
            try:
                self.redis_client.set(
                    name=key,
                    value=json.dumps(value),
                    ex=expire_seconds
                )
                return
            except Exception as e:
                logger.warning(f"Redis set failed for {key}: {e}")
                
        # In-memory fallback
        import time
        self.in_memory_cache[key] = value
        self.in_memory_expires[key] = time.time() + expire_seconds

    def delete(self, key: str):
        """Delete key from cache"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return
            except Exception as e:
                logger.warning(f"Redis delete failed for {key}: {e}")
                
        # In-memory fallback
        if key in self.in_memory_cache:
            del self.in_memory_cache[key]
        if key in self.in_memory_expires:
            del self.in_memory_expires[key]

    def delete_by_prefix(self, prefix: str):
        """Delete keys matching a prefix (cache invalidation)"""
        if self.redis_client:
            try:
                # Scan for matching keys
                keys = self.redis_client.keys(f"{prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                return
            except Exception as e:
                logger.warning(f"Redis delete_by_prefix failed for {prefix}: {e}")
                
        # In-memory fallback
        keys_to_del = [k for k in self.in_memory_cache if k.startswith(prefix)]
        for k in keys_to_del:
            self.delete(k)
