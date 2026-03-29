"""Charge App configuration — all settings from environment variables."""
import os

CORE_API = os.getenv("OCPP_CORE_API", "http://localhost:8000")
SKIN = os.getenv("SKIN", "default")
PLUGINS = os.getenv("PLUGINS", "receipts,account").split(",")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8003"))
APP_TITLE = os.getenv("APP_TITLE", "OCPP Charge")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
