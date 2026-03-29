"""Middleware: injects feature flags, skin name, account state, and language into request.state."""
import json
import os
import config
from core.flags import get_flags

import jwt

JWT_SECRET = config.JWT_SECRET
JWT_ALGO = "HS256"
COOKIE_NAME = "auth_token"

SUPPORTED_LANGS = {"nl", "en"}
DEFAULT_LANG = "nl"

# Load translations once at import time
_I18N_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "i18n.json")
try:
    with open(_I18N_PATH, encoding="utf-8") as _f:
        _TRANSLATIONS: dict = json.load(_f)
except Exception:
    _TRANSLATIONS = {"nl": {}, "en": {}}


def _detect_lang(request) -> str:
    """Detect language: cookie → query param → default nl.

    Default is always Dutch. Language only changes when the user explicitly
    selects English via the switcher (?lang=en) or a persisted cookie.
    Accept-Language header is intentionally ignored — Dutch-first policy.
    """
    # 1. Cookie (persisted explicit choice)
    cookie_lang = request.cookies.get("lang")
    if cookie_lang in SUPPORTED_LANGS:
        return cookie_lang

    # 2. Query param (explicit switcher click)
    query_lang = request.query_params.get("lang")
    if query_lang in SUPPORTED_LANGS:
        return query_lang

    return DEFAULT_LANG


async def inject_context(request, call_next):
    """Inject flags, skin, account, language, and translations into request.state."""
    request.state.flags = await get_flags()
    request.state.skin = config.SKIN

    # Decode account from JWT cookie (read-only — no DB call here)
    token = request.cookies.get(COOKIE_NAME)
    request.state.account = None
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            request.state.account = payload
        except Exception:
            # Expired or invalid token — clear silently, routes will handle redirect
            pass

    # Language detection and translation injection
    lang = _detect_lang(request)
    request.state.lang = lang
    request.state.t = _TRANSLATIONS.get(lang, _TRANSLATIONS.get(DEFAULT_LANG, {}))

    response = await call_next(request)

    # Set lang cookie if query param was used (persist the choice)
    query_lang = request.query_params.get("lang")
    if query_lang in SUPPORTED_LANGS:
        response.set_cookie("lang", query_lang, max_age=60 * 60 * 24 * 30, samesite="lax")

    return response
