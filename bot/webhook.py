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
        # VALIDASI BASIC
        # =========================
        if "message" not in data:
            return {"ok": True}

        message_data = data["message"]

        # skip kalau bukan text (image, sticker, dll)
        if "text" not in message_data:
            return {"ok": True}

        message = message_data.get("text", "").strip()
        telegram_id = str(message_data["chat"]["id"])

        if not message:
            return {"ok": True}

        # =========================
        # LOG
        # =========================
        print(f"📩 Message from {telegram_id}: {message}")

        # =========================
        # CARI OWNER (MULTI ADMIN)
        # =========================
        owner = db.query(User).filter(User.id == 1).first()

        if not owner:
            print(f"❌ Owner tidak ditemukan untuk telegram_id={telegram_id}")
            return {"ok": True}

        # =========================
        # BOT ACTIVE CHECK (OPTIONAL EXTRA SAFE)
        # =========================
        if not owner.bot_active:
            print(f"⛔ Bot OFF untuk owner {owner.id}")
            return {"ok": True}

        # =========================
        # RUN AI
        # =========================
        result = await handle_message(
            user_id=telegram_id,
            message=message,
            owner_id=owner.id
        )

        # =========================
        # SEND RESPONSE
        # =========================
        if result and result.get("reply"):
            await send_telegram(telegram_id, result["reply"])

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}

    finally:
        db.close()