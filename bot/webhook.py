from fastapi import APIRouter, Request, Depends
from database.database import SessionLocal
from database.models import User
from services.bot_engine import handle_message
from bot.telegram import send_telegram

router = APIRouter(prefix="/webhook", tags=["telegram"])


@router.post("/telegram")
async def telegram_webhook(request: Request):
    db = SessionLocal()

    try:
        data = await request.json()

        if "message" not in data:
            return {"ok": True}

        message_data = data["message"]

        message = message_data.get("text", "")
        telegram_id = str(message_data["chat"]["id"])

        if not message:
            return {"ok": True}

        print(f"📩 Message from {telegram_id}: {message}")

        # 🔥 cari owner berdasarkan telegram_id
        owner = db.query(User).filter(
            User.telegram_id == telegram_id
        ).first()

        if not owner:
            print("❌ Owner tidak ditemukan")
            return {"ok": True}

        # 🔥 kirim ke AI (pakai owner.id)
        result = await handle_message(telegram_id, message, owner.id)

        if result and result.get("reply"):
            await send_telegram(telegram_id, result["reply"])

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}

    finally:
        db.close()