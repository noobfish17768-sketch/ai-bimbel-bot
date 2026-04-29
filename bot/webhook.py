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
            {
                "request": request,
                "error": "Username & password wajib diisi"
            }
        )

    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Username atau password salah"
            }
        )

    # ✅ simpan session
    request.session["user_id"] = user.id

    return RedirectResponse("/dashboard", status_code=302)


# =========================
# LOGOUT
# =========================
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# =========================
# CREATE SUPER ADMIN (INIT ONLY)
# =========================
@router.get("/init-superadmin")
def init_superadmin(request: Request, db=Depends(get_db)):

    secret = request.query_params.get("secret")

    if secret != "init-admin-123":
        return {"error": "Unauthorized"}

    existing = db.query(User).filter(User.role == "superadmin").first()

    if existing:
        return {"msg": "Superadmin sudah ada"}

    user = User(
        username="admin",
        password=hash_password("admin123"),
        role="superadmin",      # 🔥 penting
        telegram_id=None,
        bot_active=True
    )

    db.add(user)
    db.commit()

    return {"msg": "Superadmin created"}


# =========================
# OPTIONAL: CREATE ADMIN (MANUAL API)
# =========================
@router.get("/create-admin")
def create_admin(request: Request, db=Depends(get_db)):

    # ⚠️ hanya untuk development/testing
    secret = request.query_params.get("secret")

    if secret != "init-admin-123":
        return {"error": "Unauthorized"}

    username = request.query_params.get("username")
    password = request.query_params.get("password")
    telegram_id = request.query_params.get("telegram_id")

    if not username or not password or not telegram_id:
        return {"error": "username, password, telegram_id wajib"}

    # cek duplicate
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return {"error": "Username sudah dipakai"}

    user = User(
        username=username,
        password=hash_password(password),
        role="admin",
        telegram_id=telegram_id,
        bot_active=True
    )

    db.add(user)
    db.commit()

    return {"msg": f"Admin {username} created"}