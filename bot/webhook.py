from fastapi import APIRouter, Request
from database.database import SessionLocal
from database.models import Bot
from services.bot_engine import handle_message
from bot.telegram import send_telegram

router = APIRouter(prefix="/webhook", tags=["telegram"])


@router.post("/telegram/{bot_id}")
async def telegram_webhook(bot_id: int, request: Request):
    db = SessionLocal()

    try:
        data = await request.json()

        # =========================
        # VALIDASI BASIC
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

        print(f"📩 Bot {bot_id} | {telegram_id}: {message}")

        # =========================
        # 🔍 VALIDASI BOT
        # =========================
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            print(f"❌ Bot {bot_id} tidak ditemukan")
            return {"ok": True}

        if not bot.is_active:
            print(f"⛔ Bot OFF {bot_id}")
            return {"ok": True}

        # =========================
        # 🤖 RUN AI (PAKAI BOT_ID)
        # =========================
        result = await handle_message(
            user_id=telegram_id,
            message=message,
            bot_id=bot_id   # ✅ FIX: bukan owner_id lagi
        )

        # =========================
        # 📤 SEND REPLY
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