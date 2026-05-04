from passlib.context import CryptContext
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database.models import User, Bot
from core.dependencies import get_db


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
# SESSION BASIC
# =========================
def get_session_user_id(request: Request) -> int:
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return int(user_id)


# =========================
# API VERSION (Depends)
# =========================
def get_current_user_db(
    request: Request,
    db: Session = Depends(get_db)
) -> User:

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


# =========================
# WEB VERSION (NO Depends)
# =========================
def get_current_user_web(
    request: Request,
    db: Session
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=302)

    return user


# =========================
# MULTI BOT ACCESS
# =========================
def get_current_bot(
    request: Request,
    user: User,
    db: Session
) -> Bot:

    bot_id = request.query_params.get("bot_id")

    if not bot_id:
        return None  # biar dashboard bisa fallback

    try:
        bot_id = int(bot_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid bot_id")

    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        (
            (Bot.owner_id == user.id) |
            (Bot.user_id == user.id)
        )
    ).first()

    if not bot:
        raise HTTPException(status_code=403, detail="Access denied")

    return bot