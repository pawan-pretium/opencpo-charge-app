"""Session routes: create, live view, poll, stop, cancel."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from core.api import api_get, api_post

router = APIRouter()


@router.post("/api/sessions/create")
async def create_session(request: Request):
    body = await request.json()
    # Map phone → driver_phone if needed (auth form sends "phone")
    if "phone" in body and "driver_phone" not in body:
        body["driver_phone"] = body.pop("phone")
    try:
        result = await api_post("/api/v1/public/sessions", body)
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.get("/session/{session_id}", response_class=HTMLResponse)
async def live_session(request: Request, session_id: str):
    templates = request.app.state.templates
    flags = getattr(request.state, "flags", {})
    return templates.TemplateResponse(request, "session.html", {
        "session_id": session_id,
        "flags": flags,
        "t": getattr(request.state, "t", {}),
        "lang": getattr(request.state, "lang", "nl"),
    })


@router.get("/api/sessions/{session_id}/poll")
async def poll_session(session_id: str):
    try:
        data = await api_get(f"/api/v1/public/sessions/{session_id}")
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    try:
        result = await api_post(f"/api/v1/public/sessions/{session_id}/stop", {})
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    try:
        result = await api_post(f"/api/v1/public/sessions/{session_id}/cancel", {})
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)
