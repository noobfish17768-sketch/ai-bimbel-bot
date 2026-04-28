from fastapi import APIRouter, Request

from services.bot_engine import handle_message
from bot.telegram import send_telegram

router = APIRouter(prefix="/webhook", tags=["telegram"])


# =========================
# TELEGRAM WEBHOOK
# =========================
@router.post("/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        # skip kalau bukan message
        if "message" not in data:
            return {"ok": True}

        message_data = data["message"]

        message = message_data.get("text", "")
        user_id = str(message_data["chat"]["id"])

        # 🔥 skip kalau kosong
        if not message:
            return {"ok": True}
        
        # Handle non-text (image, dll)
        if "text" not in message_data:
            return {"ok": True}

        # 🔥 logging (debug)
        print(f"📩 Message from {user_id}: {message}")

        # proses ke bot engine
        result = await handle_message(user_id, message)

        # kirim balasan
        if result and result.get("reply"):
            await send_telegram(user_id, result["reply"])

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}