from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database.models import User
from core.dependencies import get_db
from core.security import get_current_user_web, hash_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin")
def admin_page(request: Request, db=Depends(get_db)):

    user_id = get_current_user_web(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    users = db.query(User).all()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "users": users}
    )


class CreateAdmin(BaseModel):
    username: str
    password: str
    telegram_id: str


@router.post("/api/admin/create")
def create_admin(data: CreateAdmin, db=Depends(get_db)):

    user = User(
        username=data.username,
        password=hash_password(data.password),
        telegram_id=data.telegram_id,
        bot_active=True
    )

    db.add(user)
    db.commit()

    return {"success": True}