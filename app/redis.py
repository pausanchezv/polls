from typing import AsyncIterator
from dependency_injector import containers, providers
from aioredis import create_redis_pool, Redis


async def init_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await create_redis_pool(f"redis://{host}") # , password=password
    yield pool
    pool.close()
    await pool.wait_closed()


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def process(self) -> str:
        await self._redis.set("my-key", "value")
        return await self._redis.get("my-key", encoding="utf-8")


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    redis_pool = providers.Resource(
        init_redis_pool,
        host=config.redis_host,
        password=config.redis_password,
    )

    service = providers.Factory(
        Service,
        redis=redis_pool,
    )