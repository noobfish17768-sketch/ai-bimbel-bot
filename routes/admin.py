from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database.models import User
from core.dependencies import get_db
from core.security import get_current_user_web, get_current_user_db, hash_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# =========================
# ADMIN PAGE (WEB)
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
# CREATE ADMIN (API)
# =========================
class CreateAdmin(BaseModel):
    username: str
    password: str


@router.post("/api/admin/create")
def create_admin(
    data: CreateAdmin,
    user: User = Depends(get_current_user_db),
    db=Depends(get_db)
):

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # cek username
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah dipakai")

    new_user = User(
        username=data.username,
        password=hash_password(data.password),
        role="admin"
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"✅ Admin created: {new_user.username}")

    except Exception as e:
        db.rollback()
        print("❌ CREATE ADMIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Gagal create admin")

    return {"success": True}


# =========================
# DELETE ADMIN
# =========================
@router.post("/api/admin/delete/{user_id}")
def delete_admin(
    user_id: int,
    user: User = Depends(get_current_user_db),
    db=Depends(get_db)
):

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Forbidden")

    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Tidak bisa hapus diri sendiri")

    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if target.role == "superadmin":
        raise HTTPException(status_code=400, detail="Tidak bisa hapus superadmin")

    try:
        db.delete(target)
        db.commit()

        print(f"🗑️ Admin deleted: {target.username}")

    except Exception as e:
        db.rollback()
        print("❌ DELETE ADMIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Gagal delete admin")

    return {"success": True}