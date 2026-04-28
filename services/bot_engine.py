from services.ai_service import run_ai
from cache.cache import redis_client
from database.database import SessionLocal
from database.models import User


def is_bot_active(user_id: str) -> bool:

    # =========================
    # REDIS (FAST)
    # =========================
    if redis_client:
        try:
            cached = redis_client.get(f"bot:{user_id}")
            if cached is not None:
                return cached == "True"
        except Exception as e:
            print("Redis error:", e)

    # =========================
    # DB FALLBACK
    # =========================
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        return bool(user.bot_active) if user else False
    except Exception as e:
        print("DB error:", e)
        return False
    finally:
        db.close()


# =========================
# HANDLE MESSAGE
# =========================
async def handle_message(user_id: str, message: str):

    if not message:
        return None

    if not is_bot_active(user_id):
        return None

    try:
        return run_ai(user_id, message)
    except Exception as e:
        print("BOT ENGINE ERROR:", e)
        return {"reply": "System error 🙏"}