from fastapi import Depends, Request, HTTPException
from database.database import SessionLocal
from database.models import User
from typing import Generator


# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# CURRENT USER
# =========================
def get_current_user(
    request: Request,
    db=Depends(get_db)
) -> User:

    user_id = request.session.get("user_id")

    if not user_id:
        print("⚠️ Unauthorized: no session")
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        print(f"⚠️ Invalid session user_id={user_id}")
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


# =========================
# CURRENT USER ID (LIGHTWEIGHT)
# =========================
def get_current_user_id(
    request: Request
) -> int:

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return int(user_id)


# =========================
# OPTIONAL: ADMIN CHECK
# =========================
def require_admin(
    user: User = Depends(get_current_user)
) -> User:

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    return user