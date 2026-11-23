"""Who the driver is for a charging session. Decided on the server only.

Two ways a driver is known without typing a code again:

1. Remembered proof. After a correct code, the server sets a signed,
   HttpOnly cookie `driver_proof` for 30 days. It holds the phone or email
   that was verified. It is signed with JWT_SECRET, so the browser cannot
   change it.
2. Signed-in account. The `auth_token` cookie is checked by the core. The
   core returns the account's phone number.

A session is created only for an identity found here. A phone or email sent
by the browser is never trusted on its own.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from fastapi import Request

import config
from core.middleware import COOKIE_NAME, JWT_ALGO, JWT_SECRET

logger = logging.getLogger(__name__)

PROOF_COOKIE = "driver_proof"
PROOF_TTL = timedelta(days=30)
PROOF_MAX_AGE = int(PROOF_TTL.total_seconds())


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"


def issue_proof(response, *, phone: Optional[str] = None, email: Optional[str] = None) -> None:
    """Set the remembered-proof cookie after a correct code."""
    if not (phone or email):
        return
    claims = {"typ": "driver", "exp": datetime.now(timezone.utc) + PROOF_TTL}
    if phone:
        claims["phone"] = phone
    else:
        claims["email"] = email
    response.set_cookie(
        PROOF_COOKIE,
        jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGO),
        max_age=PROOF_MAX_AGE,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def clear_proof(response) -> None:
    """Forget the verified phone or email on this device."""
    response.delete_cookie(PROOF_COOKIE, path="/", samesite="lax", secure=_cookie_secure())


def _proof_identity(request: Request) -> Optional[dict]:
    raw = request.cookies.get(PROOF_COOKIE)
    if not raw:
        return None
    try:
        claims = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception:
        return None  # bad signature or expired: treat as not verified
    if claims.get("typ") != "driver":
        return None
    if claims.get("phone"):
        return {"phone": claims["phone"], "email": None, "via": "remembered"}
    if claims.get("email"):
        return {"phone": None, "email": claims["email"], "via": "remembered"}
    return None


async def _account_identity(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        async with httpx.AsyncClient(base_url=config.CORE_API, timeout=5) as client:
            r = await client.get(
                "/api/v1/public/account/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code != 200:
            return None  # not an account token, or expired
        profile = r.json()
    except Exception as exc:
        logger.warning("Account profile lookup failed: %s", exc)
        return None
    if not profile.get("phone"):
        return None  # account has no phone on file: ask for a code
    return {"phone": profile["phone"], "email": profile.get("email"), "via": "account"}


async def verified_identity(request: Request) -> Optional[dict]:
    """The verified driver for this request, or None if a code is needed."""
    return _proof_identity(request) or await _account_identity(request)


def hint(identity: dict) -> str:
    """A masked form for the screen. Never the full number or address."""
    if identity.get("phone"):
        return "••••" + identity["phone"][-4:]
    email = identity.get("email") or ""
    name, _, domain = email.partition("@")
    return (name[:2] + "•••@" + domain) if domain else ""
