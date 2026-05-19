from redis.asyncio import Redis, from_url

from backend.core.config import get_settings

settings = get_settings()

_cache_client: Redis | None = None
_redis_client: Redis | None = None


def get_cache_client() -> Redis:
    global _cache_client

    if _cache_client is None:
        base_url = str(settings.redis_url).rstrip("/")
        url = f"{base_url}/{settings.redis_cache_db}"
        _cache_client = from_url(url, decode_responses=True)

    return _cache_client


def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = from_url(str(settings.redis_url), decode_responses=True)

    return _redis_client


async def close_cache_client() -> None:
    global _cache_client
    global _redis_client

    if _cache_client is not None:
        await _cache_client.aclose()
        _cache_client = None

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None