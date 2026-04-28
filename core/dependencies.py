from typing import Generator
from fastapi import Request, HTTPException
from database.database import SessionLocal


# =========================
# DB DEPENDENCY (GLOBAL)
# =========================
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTH DEPENDENCY (GLOBAL)
# =========================
def get_current_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user_id