from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests

from database.models import Bot, User
from core.dependencies import get_db
from core.security import get_current_user_db
from cache.cache import redis_client
from core.config import settings

router = APIRouter(prefix="/api/bot", tags=["bot"])


# =========================
# REQUEST SCHEMA
# =========================
class CreateBotRequest(BaseModel):
    name: str
    telegram_token: str
    persona_type: str
    system_prompt: str | None = None


class ToggleRequest(BaseModel):
    bot_id: int
    status: bool


class UpdateBotRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    persona_type: str | None = None


# =========================
# VALID PERSONA
# =========================
VALID_PERSONA = ["bimbel", "curhat", "jualan"]


# =========================
# VALIDATE TELEGRAM TOKEN
# =========================
def validate_bot_token(token: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        res = requests.get(url).json()
        return res.get("ok", False)
    except:
        return False


# =========================
# SET WEBHOOK
# =========================
def set_webhook(token: str, bot_id: int):
    try:
        webhook_url = f"{settings.BASE_URL}/webhook/telegram/{bot_id}"

        url = f"https://api.telegram.org/bot{token}/setWebhook"

        res = requests.post(url, json={
            "url": webhook_url
        }).json()

        return res.get("ok", False)

    except Exception as e:
        print("❌ Webhook error:", e)
        return False


# =========================
# CREATE BOT
# =========================
@router.post("/create")
def create_bot(
    payload: CreateBotRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):

    # VALIDASI PERSONA
    if payload.persona_type not in VALID_PERSONA:
        raise HTTPException(status_code=400, detail="Invalid persona_type")

    # VALIDASI TOKEN
    if not validate_bot_token(payload.telegram_token):
        raise HTTPException(status_code=400, detail="Token Telegram tidak valid")

    # CEK TOKEN DUPLIKAT
    existing = db.query(Bot).filter(
        Bot.telegram_token == payload.telegram_token
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Token sudah digunakan")

    # CREATE BOT
    bot = Bot(
        owner_id=current_user.id,
        name=payload.name,
        telegram_token=payload.telegram_token,
        persona_type=payload.persona_type,
        system_prompt=payload.system_prompt,
        is_active=True
    )

    try:
        db.add(bot)
        db.commit()
        db.refresh(bot)

        print(f"🚀 BOT CREATED: {bot.id} | {bot.name}")

    except Exception as e:
        db.rollback()
        print("❌ CREATE BOT ERROR:", e)
        raise HTTPException(status_code=500, detail="Create bot failed")

    # SET WEBHOOK
    success = set_webhook(bot.telegram_token, bot.id)

    if success:
        print(f"✅ Webhook aktif untuk bot {bot.id}")
    else:
        print(f"⚠️ Webhook gagal untuk bot {bot.id}")

    return {
        "success": True,
        "bot_id": bot.id,
        "webhook": "success" if success else "failed"
    }


# =========================
# TOGGLE BOT
# =========================
@router.post("/toggle")
def toggle_bot(
    data: ToggleRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    bot = db.query(Bot).filter(
        Bot.id == data.bot_id,
        Bot.owner_id == current_user.id
    ).first()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    try:
        bot.is_active = data.status
        db.commit()

        print(f"🔁 BOT TOGGLE: {bot.id} → {data.status}")

    except Exception as e:
        db.rollback()
        print("❌ DB ERROR:", e)
        raise HTTPException(status_code=500, detail="Update failed")

    # REDIS CACHE
    if redis_client:
        try:
            redis_client.set(
                f"bot:{bot.id}",
                str(data.status),
                ex=3600
            )
        except Exception as e:
            print("⚠️ Redis error:", e)

    return {
        "success": True,
        "bot_id": bot.id,
        "is_active": data.status
    }


# =========================
# LIST
# =========================
@router.get("/list")
def list_bots(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    bots = db.query(Bot).filter(
        Bot.owner_id == current_user.id
    ).order_by(Bot.id.desc()).all()

    return {
        "bots": [
            {
                "id": b.id,
                "name": b.name,
                "persona_type": b.persona_type,
                "is_active": b.is_active,
                "created_at": b.created_at,
            }
            for b in bots
        ]
    }


# =========================
# EDIT
# =========================
@router.put("/{bot_id}")
def update_bot(
    bot_id: int,
    payload: UpdateBotRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == current_user.id
    ).first()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    try:
        if payload.name is not None:
            bot.name = payload.name

        if payload.system_prompt is not None:
            bot.system_prompt = payload.system_prompt

        if payload.persona_type is not None:
            if payload.persona_type not in VALID_PERSONA:
                raise HTTPException(status_code=400, detail="Invalid persona_type")
            bot.persona_type = payload.persona_type

        db.commit()

        print(f"✏️ BOT UPDATED: {bot.id}")

    except Exception as e:
        db.rollback()
        print("❌ UPDATE ERROR:", e)
        raise HTTPException(status_code=500, detail="Update failed")

    return {
        "success": True,
        "bot_id": bot.id
    }