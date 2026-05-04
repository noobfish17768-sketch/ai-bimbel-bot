from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database.models import User
from core.dependencies import get_db


# =========================
# 🔐 GET CURRENT USER (WEB)
# =========================
def get_current_user_web(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        return RedirectResponse("/login")

    return user


# =========================
# 🤖 GET CURRENT BOT
# =========================
def get_current_bot(request: Request, user):
    bot_id = request.query_params.get("bot_id")

    if bot_id:
        return int(bot_id)

    return None