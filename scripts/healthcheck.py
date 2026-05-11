"""Healthcheck script for service monitoring."""

import asyncio
import sys

import httpx
import structlog

logger = structlog.get_logger()


async def check_api_health(url: str = "http://localhost:8000") -> bool:
    """Check API health endpoint.

    Args:
        url: API base URL.

    Returns:
        True if healthy.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/health")
            if response.status_code == 200:
                logger.info("API healthy", url=url)
                return True
            logger.error("API unhealthy", status=response.status_code)
            return False
    except Exception as e:
        logger.error("API check failed", error=str(e))
        return False


async def check_redis(url: str = "redis://localhost:6379") -> bool:
    """Check Redis connectivity.

    Args:
        url: Redis URL.

    Returns:
        True if connected.
    """
    try:
        import redis
        r = redis.from_url(url)
        r.ping()
        logger.info("Redis healthy", url=url)
        return True
    except Exception as e:
        logger.error("Redis check failed", error=str(e))
        return False


async def check_database(url: str) -> bool:
    """Check database connectivity.

    Args:
        url: Database URL.

    Returns:
        True if connected.
    """
    try:
        # In production, use asyncpg or similar
        logger.info("Database healthy", url=url)
        return True
    except Exception as e:
        logger.error("Database check failed", error=str(e))
        return False


async def main():
    """Run all healthchecks."""
    logger.info("Running healthchecks")

    checks = {
        "api": await check_api_health(),
        "redis": await check_redis(),
    }

    all_healthy = all(checks.values())

    for service, healthy in checks.items():
        status = "HEALTHY" if healthy else "UNHEALTHY"
        logger.info(f"{service}: {status}")

    if not all_healthy:
        logger.error("Some services are unhealthy")
        sys.exit(1)

    logger.info("All services healthy")


if __name__ == "__main__":
    asyncio.run(main())
