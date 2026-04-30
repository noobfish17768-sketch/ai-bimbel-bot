from services.ai_service import run_ai
from cache.cache import redis_client
from database.database import SessionLocal
from database.models import User


# =========================
# BOT ACTIVE CHECK
# =========================
def is_bot_active(owner_id: int) -> bool:

    # REDIS CACHE
    if redis_client:
        try:
            cached = redis_client.get(f"bot:{owner_id}")
            if cached is not None:
                return cached == "True"
        except Exception as e:
            print("Redis error:", e)

    # DB FALLBACK
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == owner_id).first()
        return bool(user.bot_active) if user else False
    finally:
        db.close()


# =========================
# HANDLE MESSAGE (FINAL)
# =========================
async def handle_message(user_id: str, message: str, owner_id: int):

    if not message:
        return None

    # 🔥 cek bot owner
    if not is_bot_active(owner_id):
        print(f"🤖 Bot OFF for owner {owner_id}")
        return None

    try:
        return run_ai(
            user_id=user_id,   # 🔥 ini lead (telegram user)
            message=message,
            owner_id=owner_id # 🔥 ini admin
        )
    except Exception as e:
        print("BOT ENGINE ERROR:", e)
        return {"reply": "System error 🙏"}