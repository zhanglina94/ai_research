"""Redis client for short-term memory."""

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()


class RedisClient:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        if self._client is None:
            client = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await client.ping()
            self._client = client

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Any | None:
        await self.connect()
        assert self._client is not None
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self.connect()
        assert self._client is not None
        payload = json.dumps(value) if not isinstance(value, str) else value
        await self._client.set(key, payload, ex=ttl)

    async def delete(self, key: str) -> None:
        await self.connect()
        assert self._client is not None
        await self._client.delete(key)


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    await redis_client.connect()
    return redis_client
