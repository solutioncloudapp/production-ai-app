"""API authentication middleware."""

from typing import Any, Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def authenticate_request(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Authenticate API requests via API key or Bearer token.

    Args:
        request: FastAPI request object.
        api_key: API key from X-API-Key header.
        credentials: Bearer token credentials.

    Returns:
        Dict with authentication info.

    Raises:
        HTTPException: If authentication fails.
    """
    if settings.environment in ("development", "test") and not settings.api_secret_key:
        return {"authenticated": True, "method": "dev_mode"}

    valid_api_keys = _get_valid_api_keys()

    if api_key and api_key in valid_api_keys:
        logger.info("Authenticated via API key")
        return {"authenticated": True, "method": "api_key"}

    if credentials and credentials.credentials in valid_api_keys:
        logger.info("Authenticated via Bearer token")
        return {"authenticated": True, "method": "bearer_token"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_valid_api_keys() -> set[str]:
    """Get set of valid API keys.

    Returns:
        Set of valid API keys.
    """
    keys = set()
    if settings.api_secret_key:
        keys.add(settings.api_secret_key)
    if settings.api_secondary_key:
        keys.add(settings.api_secondary_key)
    return keys


async def authenticate_health_check(request: Request) -> dict[str, Any]:
    """Allow health check without authentication.

    Args:
        request: FastAPI request object.

    Returns:
        Dict with auth info.
    """
    return {"authenticated": True, "method": "public"}
