"""Charge App configuration — all settings from environment variables."""
import os
from urllib.parse import parse_qs, urlparse

CORE_API = os.getenv("OCPP_CORE_API_URL", os.getenv("OCPP_CORE_API", "http://localhost:8000"))
SKIN = os.getenv("SKIN", "default")
PLUGINS = os.getenv("PLUGINS", "receipts,account").split(",")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8003"))
APP_TITLE = os.getenv("APP_TITLE", "Pretium CPO")


def _carto_key(raw: str) -> str:
    """Return the CARTO key. The console value may be the key or a full tile URL."""
    value = (raw or "").strip().strip('"').strip("'")
    if "://" not in value:
        return value
    found = parse_qs(urlparse(value).query).get("key") or []
    return found[0] if found else ""


CARTO_BASEMAP_KEY = _carto_key(os.getenv("CARTO_BASEMAP_KEY", ""))
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    import secrets as _secrets
    JWT_SECRET = _secrets.token_hex(32)
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "JWT_SECRET not set — using random secret (sessions won't persist across restarts)"
    )
