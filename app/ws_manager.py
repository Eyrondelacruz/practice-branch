"""
ws_manager.py — WebSocket connection manager.
Broadcasts scan events to all connected dashboard clients.
"""
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.append(ws)

    def disconnect(self, ws: WebSocket):
        self._active.discard(ws) if hasattr(self._active, "discard") else None
        if ws in self._active:
            self._active.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps(data)
        dead = []
        for ws in self._active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
