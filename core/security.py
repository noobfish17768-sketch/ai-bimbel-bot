from passlib.context import CryptContext
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from database.database import SessionLocal
from database.models import User, Bot


# =========================
# PASSWORD
# =========================
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# =========================
# BASIC (LEGACY - KEEP)
# =========================
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    return int(user_id) if user_id else None


def require_user(request: Request):
    user_id = get_current_user(request)
    return user_id if user_id else None


# =========================
# 🔥 STRONG VERSION (API)
# =========================
def get_current_user_db(request: Request) -> User:

    db = SessionLocal()

    try:
        user_id = request.session.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user = db.query(User).filter(User.id == int(user_id)).first()

        if not user:
            request.session.clear()
            raise HTTPException(status_code=401, detail="Invalid session")

        return user

    finally:
        db.close()


# =========================
# 🔥 WEB VERSION (REDIRECT)
# =========================
def get_current_user_web(request: Request) -> User:

    db = SessionLocal()

    try:
        user_id = request.session.get("user_id")

        if not user_id:
            return RedirectResponse("/login", status_code=302)

        user = db.query(User).filter(User.id == int(user_id)).first()

        if not user:
            request.session.clear()
            return RedirectResponse("/login", status_code=302)

        return user

    finally:
        db.close()


# =========================
# 🔥 MULTI BOT (UPGRADE)
# =========================
def get_current_bot(request: Request, user: User = None):
    bot_id = request.query_params.get("bot_id")

    if not bot_id:
        return None

    try:
        bot_id = int(bot_id)
    except:
        return None

    if not user:
        return bot_id

    db = SessionLocal()
    try:

        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            (
                (Bot.owner_id == user.id) |
                (Bot.user_id == user.id)
            )
        ).first()

        return bot.id if bot else None

    finally:
        db.close()