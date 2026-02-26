"""
auth.py — API key authentication middleware.

Protects all non-health endpoints with a Bearer token check.
The API key is set via the API_KEY environment variable.

Usage:
    Set API_KEY in your .env file.
    Clients must include the header:
        Authorization: Bearer <your-api-key>

Endpoints excluded from auth:
    GET  /          — root info
    GET  /health    — liveness probe (must be reachable by Docker/k8s)
    GET  /docs      — Swagger UI
    GET  /openapi.json — OpenAPI schema
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import config
from logger import get_logger

log = get_logger(__name__)

# Endpoints that do NOT require authentication
_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Checks for a valid Bearer token on all protected routes.

    Returns 401 if the header is missing.
    Returns 403 if the token is present but invalid.
    Passes through if API_KEY is not configured (auth disabled).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no API key is configured
        if not config.API_KEY:
            return await call_next(request)

        # Skip auth for public paths
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            log.warning("auth_missing_header", extra={
                "path": request.url.path,
                "ip": request.client.host if request.client else "unknown",
            })
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": "unauthorized",
                    "message": "Authorization header required. Use: Authorization: Bearer <key>",
                },
            )

        # Expect "Bearer <token>"
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": "unauthorized",
                    "message": "Invalid Authorization format. Use: Bearer <key>",
                },
            )

        token = parts[1]
        if token != config.API_KEY:
            log.warning("auth_invalid_key", extra={
                "path": request.url.path,
                "ip": request.client.host if request.client else "unknown",
            })
            return JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "code": "forbidden",
                    "message": "Invalid API key.",
                },
            )

        return await call_next(request)