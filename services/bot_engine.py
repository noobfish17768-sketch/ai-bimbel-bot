from services.ai_service import run_ai
from cache.cache import redis_client
from database.database import SessionLocal
from database.models import User


def get_owner_by_telegram(chat_id: str):
    db = SessionLocal()
    try:
        # 🔥 mapping telegram ke owner
        return db.query(User).filter(User.telegram_id == chat_id).first()
    finally:
        db.close()


def is_bot_active(owner_id: int) -> bool:
    if redis_client:
        try:
            cached = redis_client.get(f"bot:{owner_id}")
            if cached is not None:
                return cached == "True"
        except:
            pass

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == owner_id).first()
        return bool(user.bot_active) if user else False
    finally:
        db.close()


async def handle_message(chat_id: str, message: str):

    owner = get_owner_by_telegram(chat_id)

    if not owner:
        print("❌ OWNER NOT FOUND")
        return None

    if not is_bot_active(owner.id):
        print(f"🤖 Bot OFF for owner {owner.id}")
        return None

    return run_ai(
        user_id=chat_id,
        message=message,
        owner_id=owner.id
    )