from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from database.models import User
from core.security import verify_password, hash_password
from core.dependencies import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# =========================
# LOGIN PAGE
# =========================
@router.get("/login")
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request})


# =========================
# LOGIN ACTION
# =========================
@router.post("/login")
async def login(request: Request, db=Depends(get_db)):
    form = await request.form()

    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    if not username or not password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username & password wajib diisi"}
        )

    user = db.query(User).filter_by(username=username).first()

    if user and verify_password(password, user.password):
        request.session["user_id"] = user.id
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Username atau password salah"}
    )


# =========================
# LOGOUT
# =========================
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
