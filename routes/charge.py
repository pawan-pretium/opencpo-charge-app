"""Charge screen: charger info, connector status, rate, start button."""
import json
import logging
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.api import api_get

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/charge/{cp_id}/{connector}", response_class=HTMLResponse)
async def charge_screen(request: Request, cp_id: str, connector: str):
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

    site_id = request.query_params.get("site_id", "")
    evse_id = request.query_params.get("evse_id", "")
    qr_code = request.query_params.get("qr_code", "")
    display_name = site_id if site_id else cp_id.capitalize()

    charger_data = None
    charger_error = None
    try:
        charger_data = await api_get(f"/api/v1/chargers/{cp_id}")
    except Exception as e:
        charger_error = str(e)

    conn_status = "Available"
    if charger_data:
        # Check live connector status first (real-time from OCPP heartbeat)
        live = charger_data.get("live", {})
        live_status_key = f"connector_{connector}_status"
        live_status = live.get(live_status_key) if live else None
        if live_status:
            conn_status = live_status
        else:
            # Fall back to connectors array from charger config
            for c in charger_data.get("connectors", []):
                if c.get("connector_id") == connector or c.get("id") == connector:
                    conn_status = c.get("status", "Available")
                    break

    rate_value = None
    rate_label = "Fixed rate"
    preauth_amount = "£5"
    tariff_kwh_raw = 0.0
    charger_power_kw = 0.0
    address = ""
    lat = None
    lng = None
    pricing_tier = "public"

    # Determine driver's pricing tier from cert/JWT identity
    account = getattr(request.state, "account", None)
    if account:
        pricing_tier = account.get("pricing_tier", "public")

    # Fetch dynamic tier pricing (independent of charger availability)
    try:
        pricing = await api_get("/api/v1/pricing/current")
        tier_data = pricing.get("tiers", {}).get(pricing_tier, {})
        tier_rate = tier_data.get("rate_incl")
        if tier_rate:
            tariff_kwh_raw = float(tier_rate)
            rate_value = f"£{tariff_kwh_raw:.2f}"
            rate_label = "per kWh"
    except Exception:
        pass

    if charger_data:
        meta = charger_data.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}
        # Fallback: the charger price is stored ex-VAT. The screen shows it with VAT.
        if rate_value is None:
            tariff = charger_data.get("tariff_kwh")
            if tariff is None:
                tariff = meta.get("tariff_kwh")
            if tariff is None:
                tariff = 0.50
            ex_vat = Decimal(str(tariff))
            incl = (ex_vat * Decimal("1.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tariff_kwh_raw = float(ex_vat)
            rate_value = f"£{incl:.2f}"
            rate_label = "per kWh"

        power = charger_data.get("max_power_kw") or charger_data.get("power_kw") or meta.get("max_power_kw") or 0
        charger_power_kw = float(power or 0)
        address = charger_data.get("address") or meta.get("address") or charger_data.get("location") or ""
        city = meta.get("city") or ""
        if city and city not in address:
            address = f"{address}, {city}" if address else city
        lat = charger_data.get("lat") or charger_data.get("latitude") or meta.get("latitude")
        lng = charger_data.get("lng") or charger_data.get("longitude") or meta.get("longitude")
        if not display_name or display_name == cp_id.capitalize():
            display_name = charger_data.get("name") or charger_data.get("site_name") or display_name

    return templates.TemplateResponse(request, "charge.html", {
        "cp_id": cp_id,
        "connector": connector,
        "display_name": display_name,
        "evse_id": evse_id,
        "qr_code": qr_code,
        "site_id": site_id,
        "conn_status": conn_status,
        "rate_value": rate_value,
        "rate_label": rate_label,
        "preauth_amount": preauth_amount,
        "charger_error": charger_error,
        "tariff_kwh_raw": tariff_kwh_raw,
        # Same three names are not used. The fee is on every charger except the two pilots.
        "connection_fee_pence": 0 if cp_id in {"BR75RN-1", "BR75RN-2"} else 30,
        "session_cap_pence": 18000,
        "charger_power_kw": charger_power_kw,
        "address": address,
        "lat": lat,
        "lng": lng,
        "flags": flags,
        "t": getattr(request.state, "t", {}),
        "lang": getattr(request.state, "lang", "nl"),
    })
