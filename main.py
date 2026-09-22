"""
main.py — FastAPI application entry point.
"""
import os, logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

from app.routers import scan, qr, camera, users

app = FastAPI(title="Smart School ID Attendance Scanner", version="1.0.0")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(scan.router)
app.include_router(qr.router)
app.include_router(camera.router)
app.include_router(users.router)

# ── Static files (frontend) ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
