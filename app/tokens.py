"""
tokens.py — TOTP-style 15-second rotating HMAC tokens.

Token lifecycle:
  • Each student has a per-user secret_key stored in the DB.
  • A token = HMAC-SHA256(secret_key, time_step) where time_step = floor(unix_ts / 15).
  • Verification accepts current step ± 1 (covers minor clock drift).
  • QR payload: JSON {"student_id": "STU001", "token": "<hex>"}
"""
import hmac, hashlib, time, json, struct
from typing import Tuple


STEP_SECONDS = 15          # token rotation window
DRIFT_STEPS  = 1           # ±1 window tolerance


def _time_step(ts: float | None = None) -> int:
    return int((ts or time.time()) // STEP_SECONDS)


def generate_token(secret_key: str, ts: float | None = None) -> str:
    step = _time_step(ts)
    step_bytes = struct.pack(">Q", step)          # 8-byte big-endian
    return hmac.new(
        secret_key.encode(), step_bytes, hashlib.sha256
    ).hexdigest()


def verify_token(secret_key: str, token: str) -> Tuple[bool, str]:
    """
    Returns (is_valid, reason).
    Checks current step and ±DRIFT_STEPS windows.
    """
    now_step = _time_step()
    for delta in range(-DRIFT_STEPS, DRIFT_STEPS + 1):
        expected = generate_token(secret_key, (now_step + delta) * STEP_SECONDS)
        if hmac.compare_digest(expected, token):
            return True, "ok"
    return False, "expired_or_invalid"


def build_qr_payload(student_id: str, secret_key: str) -> str:
    """Return JSON string to encode into the QR code."""
    return json.dumps({"student_id": student_id, "token": generate_token(secret_key)})


def seconds_until_next_step() -> int:
    """Remaining seconds in the current 15-second window."""
    return STEP_SECONDS - int(time.time() % STEP_SECONDS)
