"""OCPP Charge App — PWA for EV drivers."""
import os
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from core.middleware import inject_context
from plugins import discover_plugins

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=config.APP_TITLE, docs_url=None, redoc_url=None)

# ── Static files ──────────────────────────────────────────────────────────
# Skin static served at /skin (takes precedence in templates)
skin_static = f"skins/{config.SKIN}/static"
if os.path.isdir(skin_static):
    app.mount("/skin", StaticFiles(directory=skin_static), name="skin")

# Base static always available at /static (home.js, htmx, logos, fallback CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Templates ─────────────────────────────────────────────────────────────
# Resolution order: skin templates → plugin templates → base templates
template_dirs = []
skin_templates = f"skins/{config.SKIN}/templates"
if os.path.isdir(skin_templates):
    template_dirs.append(skin_templates)
# Add plugin template directories
for plugin_name in config.PLUGINS:
    plugin_tmpl = f"plugins/{plugin_name}/templates"
    if os.path.isdir(plugin_tmpl):
        template_dirs.append(plugin_tmpl)
template_dirs.append("templates")

templates = Jinja2Templates(directory=template_dirs)


def uk_phone(raw) -> str:
    """Show a UK mobile as +44 7700 900 123. Other numbers stay as stored."""
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 11:
        digits = "44" + digits[1:]
    if digits.startswith("44") and len(digits) == 12:
        rest = digits[2:]
        return f"+44 {rest[:4]} {rest[4:7]} {rest[7:]}"
    return str(raw or "").strip()


templates.env.filters["uk_phone"] = uk_phone
templates.env.globals["app_title"] = config.APP_TITLE
app.state.templates = templates

# ── Routes ────────────────────────────────────────────────────────────────
from routes import home, charge, auth, session, receipt, qr, push, cert_setup

for router in [home.router, charge.router, auth.router, session.router, receipt.router, qr.router, push.router, cert_setup.router]:
    app.include_router(router)

# ── Plugins ───────────────────────────────────────────────────────────────
for plugin_router in discover_plugins(config.PLUGINS):
    app.include_router(plugin_router)

# ── Middleware ────────────────────────────────────────────────────────────
app.middleware("http")(inject_context)

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.APP_HOST, port=config.APP_PORT, reload=True)
