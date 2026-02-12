from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/analyses/{analysis_id}")
async def analysis_progress(websocket: WebSocket, analysis_id: str) -> None:
    """분석 진행 상황을 실시간으로 전달합니다."""
    await websocket.accept()
    try:
        # TODO: 실제 분석 진행 상황 구독 로직 구현
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"analysis_id": analysis_id, "message": data})
    except WebSocketDisconnect:
        pass
