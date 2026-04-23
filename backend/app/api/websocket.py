from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def events_ws(ws: WebSocket) -> None:
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep the connection alive; clients send no messages in this flow
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
