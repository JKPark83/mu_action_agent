"""WebSocket endpoint for real-time analysis progress."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/analyses/{analysis_id}")
async def analysis_progress(websocket: WebSocket, analysis_id: str) -> None:
    """분석 진행 상황을 실시간으로 전달합니다."""
    await manager.connect(analysis_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        manager.disconnect(analysis_id, websocket)
