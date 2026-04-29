from fastapi import Depends, Request, HTTPException
from database.database import SessionLocal
from database.models import User
from typing import Generator


# =========================
# DB SESSION
# =========================
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# CURRENT USER (FULL VALIDATION)
# =========================
def get_current_user(
    request: Request,
    db=Depends(get_db)
) -> User:

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")

    return user