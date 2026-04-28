from passlib.context import CryptContext
from fastapi import Request

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# PASSWORD
# =========================
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def hash_password(password):
    return pwd_context.hash(password)


# =========================
# AUTH HELPERS
# =========================
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    return int(user_id) if user_id else None


def require_user(request: Request):
    """
    Helper untuk memastikan user login
    """
    user_id = get_current_user(request)
    if not user_id:
        return None
    return user_id