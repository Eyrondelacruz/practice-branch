"""
routers/scan.py — Core scan endpoint + WebSocket hub.

POST /api/scan        — validate QR payload, log attendance, trigger notifications
GET  /api/logs/today  — return today's attendance log
WS   /ws/scan         — real-time push to dashboard
"""
import json, logging
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.tokens       import verify_token
from app.database     import get_user_by_custom_id, get_recent_log, get_last_log_today, insert_log, get_logs_today
from app.notifications import notify
from app.ws_manager   import manager

router = APIRouter()
log    = logging.getLogger(__name__)


class ScanPayload(BaseModel):
    student_id: str
    token: str


@router.post("/api/scan")
async def process_scan(payload: ScanPayload, bg: BackgroundTasks):
    # 1. Look up user
    user = get_user_by_custom_id(payload.student_id)
    if not user:
        await manager.broadcast({"status": "error", "message": "Unknown ID"})
        raise HTTPException(404, "User not found")

    # 2. Verify rotating token
    valid, reason = verify_token(user["secret_key"], payload.token)
    if not valid:
        await manager.broadcast({
            "status": "error",
            "message": "QR code expired or invalid",
            "user": _safe_user(user),
        })
        raise HTTPException(401, reason)

    # 3. Duplicate-scan guard (2-minute cooldown)
    recent = get_recent_log(user["id"], within_seconds=120)
    if recent:
        await manager.broadcast({
            "status": "duplicate",
            "message": "Already scanned within 2 minutes",
            "user": _safe_user(user),
        })
        raise HTTPException(429, "Duplicate scan")

    # 4. Determine TIME_IN / TIME_OUT
    last_today = get_last_log_today(user["id"])
    scan_type  = "TIME_OUT" if last_today and last_today["scan_type"] == "TIME_IN" else "TIME_IN"

    # 5. Persist log
    log_entry = insert_log(user["id"], scan_type)

    # 6. Broadcast success to all dashboard clients
    result = {
        "status":    "success",
        "scan_type": scan_type,
        "scanned_at": log_entry["scanned_at"],
        "user":      _safe_user(user),
    }
    await manager.broadcast(result)

    # 7. Async notifications (non-blocking)
    bg.add_task(notify, user, scan_type, log_entry["scanned_at"])

    return result


@router.get("/api/logs/today")
def logs_today():
    return get_logs_today(limit=100)


@router.websocket("/ws/scan")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep-alive; client may send pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


def _safe_user(u: dict) -> dict:
    return {k: u[k] for k in ("id", "custom_id", "full_name", "role", "photo_url") if k in u}
