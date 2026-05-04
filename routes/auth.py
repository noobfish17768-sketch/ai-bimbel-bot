from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from database.models import User
from core.security import verify_password
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

    if not user:
        print(f"❌ LOGIN FAIL (user not found): {username}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username atau password salah"}
        )

    # OPTIONAL: kalau nanti ada field is_active
    # if not user.is_active:
    #     return templates.TemplateResponse(
    #         "login.html",
    #         {"request": request, "error": "Akun nonaktif"}
    #     )

    if not verify_password(password, user.password):
        print(f"❌ LOGIN FAIL (wrong password): {username}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username atau password salah"}
        )

    # 🔥 SUCCESS LOGIN
    request.session.clear()  # penting (anti session fixation)
    request.session["user_id"] = user.id

    print(f"✅ LOGIN SUCCESS: {username}")

    return RedirectResponse("/dashboard", status_code=302)


# =========================
# LOGOUT
# =========================
@router.get("/logout")
def logout(request: Request):
    user_id = request.session.get("user_id")

    request.session.clear()

    print(f"👋 LOGOUT: {user_id}")

    return RedirectResponse("/login", status_code=302)