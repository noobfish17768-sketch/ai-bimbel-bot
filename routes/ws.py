from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.ws_manager import manager

router = APIRouter()


# =========================
# 🔌 WEBSOCKET ENDPOINT
# =========================
@router.websocket("/ws/{lead_id}")
async def websocket_endpoint(websocket: WebSocket, lead_id: int):
    await manager.connect(lead_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # =========================
            # ✍️ TYPING INDICATOR
            # =========================
            if data.get("type") == "typing":
                await manager.send_to_lead(lead_id, {
                    "type": "typing",
                    "from": data.get("from", "admin")
                })

            elif data.get("type") == "typing_stop":
                await manager.send_to_lead(lead_id, {
                    "type": "typing_stop"
                })

            # =========================
            # 💬 MESSAGE (OPTIONAL FUTURE)
            # =========================
            elif data.get("type") == "message":
                await manager.send_to_lead(lead_id, {
                    "type": "message",
                    "from": data.get("from", "admin"),
                    "text": data.get("text")
                })

    except WebSocketDisconnect:
        manager.disconnect(lead_id, websocket)