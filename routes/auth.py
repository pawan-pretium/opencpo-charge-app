"""Auth routes: OTP flow for driver identification."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import HTTPException

from core.api import api_post

router = APIRouter()


@router.get("/auth/{cp_id}/{connector}", response_class=HTMLResponse)
async def auth_screen(request: Request, cp_id: str, connector: int):
    templates = request.app.state.templates
    flags = getattr(request.state, "flags", {})
    return templates.TemplateResponse(request, "auth.html", {
        "cp_id": cp_id,
        "connector": connector,
        "flags": flags,
        "t": getattr(request.state, "t", {}),
        "lang": getattr(request.state, "lang", "nl"),
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
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)
