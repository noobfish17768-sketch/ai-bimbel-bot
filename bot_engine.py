from ai_service import run_ai
from cache import redis_client
from database import SessionLocal
from models import User

def is_bot_active(user_id):
    cached = redis_client.get(f"bot:{user_id}")

    if cached is not None:
        return cached == "True"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user.bot_active if user else False
    finally:
        db.close()


async def handle_message(user_id, message):
    if not is_bot_active(user_id):
        return None

    return await run_ai(user_id, message)