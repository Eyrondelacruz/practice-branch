"""
routers/qr.py — Generate a fresh QR code PNG for a given student_id.

GET /api/qr/{student_id}  — returns PNG image (refreshes every 15 s)
GET /api/token-info        — returns seconds remaining in current window
"""
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import qrcode

from app.tokens   import build_qr_payload, seconds_until_next_step, generate_token
from app.database import get_user_by_custom_id

router = APIRouter()


@router.get("/api/qr-payload/{student_id}")
def get_qr_payload(student_id: str):
    """Return JSON payload for manual scan testing."""
    user = get_user_by_custom_id(student_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {"student_id": student_id, "token": generate_token(user["secret_key"])}


@router.get("/api/qr/{student_id}")
def get_qr(student_id: str):
    user = get_user_by_custom_id(student_id)
    if not user:
        raise HTTPException(404, "User not found")

    payload = build_qr_payload(student_id, user["secret_key"])
    img = qrcode.make(payload)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/token-info")
def token_info():
    return JSONResponse({"seconds_remaining": seconds_until_next_step()})
