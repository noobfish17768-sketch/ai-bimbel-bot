from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database.models import User
from core.dependencies import get_db
from core.security import get_current_user_web, hash_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# =========================
# ADMIN PAGE
# =========================
@router.get("/admin")
def admin_page(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request)

    if not hasattr(user, "id"):
        return user

    if user.role != "superadmin":
        return RedirectResponse("/dashboard", status_code=302)

    users = db.query(User).all()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "users": users
        }
    )


# =========================
# CREATE ADMIN
# =========================
class CreateAdmin(BaseModel):
    username: str
    password: str
    telegram_id: str


@router.post("/api/admin/create")
def create_admin(request: Request, data: CreateAdmin, db=Depends(get_db)):

    user = get_current_user_web(request)

    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # validasi input
    if not data.telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id wajib diisi")

    # cek username
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah dipakai")

    # cek telegram_id
    existing_tg = db.query(User).filter(User.telegram_id == data.telegram_id).first()
    if existing_tg:
        raise HTTPException(status_code=400, detail="Telegram ID sudah dipakai")

    new_user = User(
        username=data.username,
        password=hash_password(data.password),
        telegram_id=data.telegram_id,
        role="admin",
        bot_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"success": True}


# =========================
# DELETE ADMIN
# =========================
@router.post("/api/admin/delete/{user_id}")
def delete_admin(user_id: int, request: Request, db=Depends(get_db)):

    user = get_current_user_web(request)

    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # ❌ jangan hapus diri sendiri
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Tidak bisa hapus diri sendiri")

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # ❌ jangan hapus superadmin lain (optional safety)
    if target.role == "superadmin":
        raise HTTPException(status_code=400, detail="Tidak bisa hapus superadmin")

    db.delete(target)
    db.commit()

    return {"success": True}