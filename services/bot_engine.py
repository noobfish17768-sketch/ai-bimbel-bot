from services.ai_service import run_ai
from cache.cache import redis_client
from database.database import SessionLocal
from database.models import User


# =========================
# BOT ACTIVE CHECK
# =========================
def is_bot_active(owner_id: int) -> bool:

    # 🔥 REDIS CACHE (optional)
    if redis_client:
        try:
            cached = redis_client.get(f"bot:{owner_id}")
            if cached is not None:
                return cached.decode() == "True"
        except Exception as e:
            print("Redis error:", e)

    # 🔥 DB FALLBACK
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == owner_id).first()

        if not user:
            return False

        return bool(user.bot_active)

    finally:
        db.close()


# =========================
# HANDLE MESSAGE (MULTI BOT READY)
# =========================
async def handle_message(user_id: str, message: str, owner_id: int):

    # validasi basic
    if not message or not owner_id:
        return None

    # 🔥 cek bot aktif
    if not is_bot_active(owner_id):
        print(f"🤖 Bot OFF for owner {owner_id}")
        return None

    try:
        result = run_ai(
            user_id=str(user_id),   # telegram user
            message=message,
            owner_id=owner_id      # 🔥 ini jadi identitas bot
        )

        return result

    except Exception as e:
        print("BOT ENGINE ERROR:", e)
        return {"reply": "System error 🙏"}