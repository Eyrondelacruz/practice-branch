"""
routers/camera.py — OpenCV webcam capture + QR decoding.

GET  /api/camera/stream   — MJPEG stream for the live preview
POST /api/camera/start    — start background capture thread
POST /api/camera/stop     — stop capture thread
"""
import cv2, json, threading, logging, asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import httpx

log    = logging.getLogger(__name__)
router = APIRouter()

# ── Shared state ───────────────────────────────────────────────────────────────
_cap:    cv2.VideoCapture | None = None
_thread: threading.Thread | None = None
_running = threading.Event()
_latest_frame: bytes | None = None
_frame_lock = threading.Lock()
_qr_detector = cv2.QRCodeDetector()


# ── Background capture thread ──────────────────────────────────────────────────
def _capture_loop(base_url: str):
    global _cap, _latest_frame
    _cap = cv2.VideoCapture(0)
    if not _cap.isOpened():
        log.error("Cannot open webcam")
        _running.clear()
        return

    last_scanned_token = None   # simple per-frame dedup

    while _running.is_set():
        ok, frame = _cap.read()
        if not ok:
            continue

        # ── QR detection ──────────────────────────────────────────────────────
        data, _, _ = _qr_detector.detectAndDecode(frame)
        if data:
            try:
                payload = json.loads(data)
                token_key = payload.get("token", "")
                if token_key != last_scanned_token:
                    last_scanned_token = token_key
                    # Fire-and-forget HTTP call to our own scan endpoint
                    threading.Thread(
                        target=_post_scan, args=(base_url, payload), daemon=True
                    ).start()
            except (json.JSONDecodeError, KeyError):
                pass

        # ── Encode frame as JPEG ──────────────────────────────────────────────
        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with _frame_lock:
            _latest_frame = jpeg.tobytes()

    _cap.release()
    _cap = None


def _post_scan(base_url: str, payload: dict):
    try:
        httpx.post(
            f"{base_url}/api/scan",
            json={"student_id": payload["student_id"], "token": payload["token"]},
            timeout=5,
        )
    except Exception as exc:
        log.debug("Scan post error: %s", exc)


# ── MJPEG generator ────────────────────────────────────────────────────────────
def _mjpeg_generator():
    import time
    while _running.is_set():
        with _frame_lock:
            frame = _latest_frame
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        else:
            time.sleep(0.05)


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.get("/api/camera/stream")
def camera_stream():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/api/camera/start")
def camera_start(base_url: str = "http://localhost:8000"):
    global _thread
    if _running.is_set():
        return {"status": "already_running"}
    _running.set()
    _thread = threading.Thread(target=_capture_loop, args=(base_url,), daemon=True)
    _thread.start()
    return {"status": "started"}


@router.post("/api/camera/stop")
def camera_stop():
    _running.clear()
    return {"status": "stopped"}
