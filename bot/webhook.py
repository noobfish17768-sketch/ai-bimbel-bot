from fastapi import APIRouter, Request
from database.database import SessionLocal
from database.models import Bot, User
from services.bot_engine import handle_message
from bot.telegram import send_telegram

router = APIRouter(prefix="/webhook", tags=["telegram"])


@router.post("/telegram/{bot_id}")
async def telegram_webhook(bot_id: int, request: Request):
    db = SessionLocal()

    try:
        data = await request.json()

        if "message" not in data:
            return {"ok": True}

        message_data = data["message"]

        if "text" not in message_data:
            return {"ok": True}

        message = message_data.get("text", "").strip()
        telegram_id = str(message_data["chat"]["id"])

        if not message:
            return {"ok": True}

        print(f"📩 Bot {bot_id} | {telegram_id}: {message}")

        # =========================
        # 🔥 VALIDASI BOT
        # =========================
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            print("❌ Bot tidak ditemukan")
            return {"ok": True}

        owner_id = bot.user_id

        owner = db.query(User).filter(User.id == owner_id).first()

        if not owner or not owner.bot_active:
            print(f"⛔ Bot OFF owner {owner_id}")
            return {"ok": True}

        # =========================
        # RUN AI
        # =========================
        result = await handle_message(
            user_id=telegram_id,
            message=message,
            owner_id=owner_id
        )

        # =========================
        # SEND REPLY (🔥 pakai bot_id)
        # =========================
        if result and result.get("reply"):
            await send_telegram(
                bot_id=bot_id,
                chat_id=telegram_id,
                text=result["reply"]
            )

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}

    finally:
        db.close()