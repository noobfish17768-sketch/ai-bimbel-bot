from passlib.context import CryptContext
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from database.database import SessionLocal
from database.models import User


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
    """
    ⚠️ Simple version (NO DB CHECK)
    Keep for backward compatibility only
    """
    user_id = request.session.get("user_id")
    return int(user_id) if user_id else None


def require_user(request: Request):
    """
    Legacy helper
    """
    user_id = get_current_user(request)
    return user_id if user_id else None


# =========================
# 🔥 STRONG VERSION (API)
# =========================
def get_current_user_db(request: Request) -> User:
    """
    ✅ Recommended for API / backend
    - Validates session
    - Validates user exists in DB
    - Raises HTTPException if invalid
    """

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
    """
    ✅ Recommended for HTML pages
    - Redirects to /login instead of JSON error
    """

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