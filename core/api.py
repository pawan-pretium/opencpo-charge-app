"""Thin HTTP proxy to the OCPP Core API."""
import logging

import httpx
from fastapi import HTTPException

import config

logger = logging.getLogger(__name__)


async def api_get(path: str) -> dict:
    """GET request to Core API. Raises HTTPException on failure."""
    async with httpx.AsyncClient(base_url=config.CORE_API, timeout=10) as client:
        r = await client.get(path)
        r.raise_for_status()
        return r.json()


async def api_post(path: str, body: dict) -> dict:
    """POST request to Core API. Raises HTTPException with API error detail."""
    async with httpx.AsyncClient(base_url=config.CORE_API, timeout=10) as client:
        r = await client.post(path, json=body)
        if not r.is_success:
            try:
                err = r.json()
                detail = err.get("detail", f"API error {r.status_code}")
            except Exception:
                detail = f"API error {r.status_code}"
            raise HTTPException(status_code=r.status_code, detail=detail)
        return r.json()
