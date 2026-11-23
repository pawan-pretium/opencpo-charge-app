"""Auth routes: OTP flow for driver identification."""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import HTTPException

from core.api import api_post
from core.driver_identity import clear_proof, hint, issue_proof, verified_identity

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/auth/{cp_id}/{connector}", response_class=HTMLResponse)
async def auth_screen(request: Request, cp_id: str, connector: str):
    try:
        connector = int(connector)
    except (ValueError, TypeError):
        logger.error(f"Invalid connector '{connector}' for {cp_id} — refusing to default")
        templates = request.app.state.templates
        flags = getattr(request.state, "flags", {})
        return templates.TemplateResponse(request, "error.html", {
            "message": "Invalid connector",
            "detail": "The connector could not be determined. Please scan the QR code again.",
            "flags": flags,
            "t": getattr(request.state, "t", {}),
            "lang": getattr(request.state, "lang", "nl"),
        }, status_code=400)
    templates = request.app.state.templates
    flags = getattr(request.state, "flags", {})
    identity = await verified_identity(request)
    return templates.TemplateResponse(request, "auth.html", {
        "cp_id": cp_id,
        "connector": connector,
        "flags": flags,
        "t": getattr(request.state, "t", {}),
        "lang": getattr(request.state, "lang", "nl"),
        "already_verified": identity is not None,
        "verified_hint": hint(identity) if identity else "",
    })


@router.post("/api/auth/send-otp")
async def send_otp(request: Request):
    body = await request.json()
    try:
        result = await api_post("/api/v1/public/auth/send-otp", {"phone": body.get("phone")})
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/auth/verify-otp")
async def verify_otp(request: Request):
    body = await request.json()
    try:
        result = await api_post("/api/v1/public/auth/verify-otp", {
            "phone": body.get("phone"),
            "code": body.get("code"),
        })
        resp = JSONResponse(result)
        if result.get("token") and not result.get("error"):
            issue_proof(resp, phone=result.get("phone") or body.get("phone"))
        return resp
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/auth/send-email-otp")
async def send_email_otp(request: Request):
    """Ask the core to email a verification code."""
    body = await request.json()
    try:
        result = await api_post("/api/v1/public/auth/send-email-otp", {"email": body.get("email")})
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/auth/verify-email-otp")
async def verify_email_otp(request: Request):
    """Check an emailed verification code."""
    body = await request.json()
    try:
        result = await api_post("/api/v1/public/auth/verify-email-otp", {
            "email": body.get("email"),
            "code": body.get("code"),
        })
        resp = JSONResponse(result)
        if result.get("token") and not result.get("error"):
            issue_proof(resp, email=result.get("email") or body.get("email"))
        return resp
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/auth/forget")
async def forget_verification():
    """Forget the remembered phone or email on this device."""
    resp = JSONResponse({"ok": True})
    clear_proof(resp)
    return resp
