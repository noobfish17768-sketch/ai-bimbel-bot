from fastapi import APIRouter, Request
from database.database import SessionLocal
from database.models import User
from services.bot_engine import handle_message
from bot.telegram import send_telegram

router = APIRouter(prefix="/webhook", tags=["telegram"])


# =========================
# TELEGRAM WEBHOOK
# =========================
@router.post("/telegram")
async def telegram_webhook(request: Request):
    db = SessionLocal()

    try:
        data = await request.json()

        # =========================
        # VALIDASI
        # =========================
        if "message" not in data:
            return {"ok": True}

        message_data = data["message"]

        if "text" not in message_data:
            return {"ok": True}

        message = message_data.get("text", "").strip()
        telegram_id = str(message_data["chat"]["id"])

        if not message:
            return {"ok": True}

        print(f"📩 Message from {telegram_id}: {message}")

        # =========================
        # 🔥 GET OWNER (DEFAULT / SINGLE BOT MODE)
        # =========================
        owner = db.query(User).filter(User.role == "admin").first()

        if not owner:
            print("❌ Tidak ada admin di database")
            return {"ok": True}

        # =========================
        # BOT STATUS
        # =========================
        if not owner.bot_active:
            print(f"⛔ Bot OFF untuk owner {owner.id}")
            return {"ok": True}

        # =========================
        # RUN AI
        # =========================
        result = await handle_message(
            user_id=telegram_id,   # lead
            message=message,
            owner_id=owner.id      # admin
        )

        # =========================
        # SEND REPLY
        # =========================
        if result and result.get("reply"):
            await send_telegram(telegram_id, result["reply"])

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}

    finally:
        db.close()