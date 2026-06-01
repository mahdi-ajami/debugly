import json
import logging
import threading
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

_redis_available = False
_redis_client = None
_pubsub = None

try:
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    logger.debug("redis not installed; using in-memory cache fallback")


class CacheBackend:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    async def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._store.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        with self._lock:
            self._store[key] = value

    async def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    async def publish(self, channel: str, message: Any):
        pass

    async def subscribe(self, channel: str, callback: Callable):
        pass

    async def close(self):
        self._store.clear()


class RedisBackend(CacheBackend):
    def __init__(self, url: str = "redis://localhost:6379/0"):
        super().__init__()
        self._url = url
        self._redis = None
        self._pubsub = None

    async def _ensure(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        await self._ensure()
        try:
            return await self._redis.get(key)
        except Exception:
            return await super().get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        await self._ensure()
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception:
            await super().set(key, value, ttl)

    async def delete(self, key: str):
        await self._ensure()
        try:
            await self._redis.delete(key)
        except Exception:
            await super().delete(key)

    async def publish(self, channel: str, message: Any):
        await self._ensure()
        try:
            msg = json.dumps({"data": message}, default=str)
            await self._redis.publish(channel, msg)
        except Exception:
            pass

    async def subscribe(self, channel: str, callback: Callable):
        await self._ensure()
        try:
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(channel)

            async def _listener():
                while True:
                    try:
                        msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if msg:
                            data = json.loads(msg["data"])
                            await callback(data.get("data", data))
                    except Exception:
                        break

            threading.Thread(target=lambda: asyncio.run(_listener()), daemon=True).start()
        except Exception:
            pass

    async def close(self):
        if self._pubsub:
            await self._pubsub.unsubscribe()
        if self._redis:
            await self._redis.close()


import asyncio

_cache: CacheBackend = CacheBackend()


async def init_cache(redis_url: str = ""):
    global _cache
    if redis_url and _redis_available:
        try:
            _cache = RedisBackend(redis_url)
            await _cache._ensure()
            logger.info("Connected to Redis at %s", redis_url)
        except Exception as e:
            logger.warning("Redis connection failed (%s); using in-memory cache", e)
            _cache = CacheBackend()
    return _cache


def get_cache() -> CacheBackend:
    return _cache


async def close_cache():
    await _cache.close()
