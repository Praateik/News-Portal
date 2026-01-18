"""
Redis caching layer for production-grade news platform.

Cache Strategy:
- article:{hash}:content   → Full article content (24h TTL)
- article:{hash}:summary   → AI-generated summary (24h TTL)
- article:{hash}:image     → Generated image URL (7d TTL)
- article:{hash}:meta      → Metadata bundle (24h TTL)

All AI operations are cached to ensure <200ms TTFB on repeat requests.
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any
import redis
from redis import Redis
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis caching with fallback to in-memory cache"""
    
    # TTL Constants (in seconds)
    TTL_CONTENT = 86400      # 24 hours
    TTL_SUMMARY = 86400      # 24 hours
    TTL_IMAGE = 604800       # 7 days
    TTL_META = 86400         # 24 hours
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
                      Falls back to env var REDIS_URL if not provided
        """
        self.enabled = False
        self.client: Optional[Redis] = None
        self.memory_cache: Dict[str, tuple] = {}  # Fallback in-memory cache
        
        try:
            url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
            # Test connection
            self.client.ping()
            self.enabled = True
            logger.info("✓ Redis cache enabled and connected")
        except Exception as e:
            logger.warning(f"⚠ Redis connection failed: {e}. Using in-memory fallback.")
            self.enabled = False
            self.client = None
    
    @staticmethod
    def _hash_url(url: str) -> str:
        """Generate consistent hash for URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    @staticmethod
    def _make_key(prefix: str, url_hash: str, suffix: str = "") -> str:
        """Generate cache key: article:{hash}:{suffix}"""
        return f"article:{url_hash}:{suffix}" if suffix else f"article:{url_hash}"
    
    # ========================================================================
    # Content Operations
    # ========================================================================
    
    def get_content(self, url: str) -> Optional[str]:
        """Retrieve cached article content"""
        key = self._make_key("article", self._hash_url(url), "content")
        return self._get(key)
    
    def set_content(self, url: str, content: str) -> bool:
        """Cache article content (24h TTL)"""
        key = self._make_key("article", self._hash_url(url), "content")
        return self._set(key, content, self.TTL_CONTENT)
    
    # ========================================================================
    # Summary Operations (AI Generated)
    # ========================================================================
    
    def get_summary(self, url: str) -> Optional[str]:
        """Retrieve cached AI summary"""
        key = self._make_key("article", self._hash_url(url), "summary")
        return self._get(key)
    
    def set_summary(self, url: str, summary: str) -> bool:
        """Cache AI-generated summary (24h TTL)"""
        key = self._make_key("article", self._hash_url(url), "summary")
        return self._set(key, summary, self.TTL_SUMMARY)
    
    # ========================================================================
    # Image Operations (AI Generated)
    # ========================================================================
    
    def get_image(self, url: str) -> Optional[str]:
        """Retrieve cached image URL"""
        key = self._make_key("article", self._hash_url(url), "image")
        return self._get(key)
    
    def set_image(self, url: str, image_url: str) -> bool:
        """Cache generated image URL (7d TTL)"""
        key = self._make_key("article", self._hash_url(url), "image")
        return self._set(key, image_url, self.TTL_IMAGE)
    
    # ========================================================================
    # Metadata Operations (Bundle)
    # ========================================================================
    
    def get_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached article metadata as JSON"""
        key = self._make_key("article", self._hash_url(url), "meta")
        data = self._get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in metadata cache for {url}")
                return None
        return None
    
    def set_metadata(self, url: str, metadata: Dict[str, Any]) -> bool:
        """Cache metadata bundle as JSON (24h TTL)"""
        key = self._make_key("article", self._hash_url(url), "meta")
        try:
            data = json.dumps(metadata)
            return self._set(key, data, self.TTL_META)
        except json.JSONEncodeError as e:
            logger.error(f"Failed to serialize metadata: {e}")
            return False
    
    # ========================================================================
    # Low-level Operations
    # ========================================================================
    
    def _get(self, key: str) -> Optional[str]:
        """Get value from Redis or memory cache"""
        try:
            if self.enabled and self.client:
                value = self.client.get(key)
                if value:
                    return value
        except Exception as e:
            logger.warning(f"Redis GET failed for {key}: {e}")
        
        # Fallback to memory cache
        if key in self.memory_cache:
            value, ttl_end = self.memory_cache[key]
            import time
            if time.time() < ttl_end:
                return value
            else:
                del self.memory_cache[key]
        
        return None
    
    def _set(self, key: str, value: str, ttl: int) -> bool:
        """Set value in Redis or memory cache with TTL"""
        try:
            if self.enabled and self.client:
                self.client.setex(key, ttl, value)
                return True
        except Exception as e:
            logger.warning(f"Redis SET failed for {key}: {e}")
        
        # Fallback to memory cache
        import time
        self.memory_cache[key] = (value, time.time() + ttl)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.enabled and self.client:
                self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE failed for {key}: {e}")
        
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        return True
    
    def flush_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        try:
            if self.enabled and self.client:
                self.client.flushdb()
        except Exception as e:
            logger.warning(f"Redis FLUSHDB failed: {e}")
        
        self.memory_cache.clear()
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis health status"""
        status = {
            "redis_enabled": self.enabled,
            "redis_connected": False,
            "memory_cache_items": len(self.memory_cache)
        }
        
        if self.enabled and self.client:
            try:
                self.client.ping()
                status["redis_connected"] = True
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
        
        return status


# Global singleton instance
redis_cache: Optional[RedisCache] = None


def init_redis_cache(redis_url: Optional[str] = None) -> RedisCache:
    """Initialize global Redis cache instance"""
    global redis_cache
    redis_cache = RedisCache(redis_url)
    return redis_cache


def get_redis_cache() -> RedisCache:
    """Get global Redis cache instance"""
    global redis_cache
    if redis_cache is None:
        redis_cache = RedisCache()
    return redis_cache
