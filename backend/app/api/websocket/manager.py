"""WebSocket ConnectionManager for real-time analysis progress updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.websocket")


@dataclass
class ConnectionManager:
    """Manages WebSocket connections grouped by analysis_id."""

    _connections: dict[str, list[WebSocket]] = field(default_factory=dict)

    async def connect(self, analysis_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if analysis_id not in self._connections:
            self._connections[analysis_id] = []
        self._connections[analysis_id].append(websocket)
        logger.debug("ws connected: analysis_id=%s", analysis_id)

    def disconnect(self, analysis_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(analysis_id)
        if conns is None:
            return
        try:
            conns.remove(websocket)
        except ValueError:
            pass
        if not conns:
            del self._connections[analysis_id]
        logger.debug("ws disconnected: analysis_id=%s", analysis_id)

    async def send_progress(self, analysis_id: str, data: dict[str, Any]) -> None:
        """Broadcast a progress message to all clients watching this analysis."""
        conns = self._connections.get(analysis_id)
        if conns is None:
            return
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(analysis_id, ws)


manager = ConnectionManager()
