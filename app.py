print("🚀 START APP")

import os
import asyncio
import threading

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from passlib.context import CryptContext
from telegram import Bot

from pydantic import BaseModel

from database import engine, Base, SessionLocal
from models import LeadDB, Conversation, BotSetting, User

from cache import redis_client
from bot_engine import handle_message

from ai_service import run_ai
from followup import run_followup

print("✅ Import OK")

app = FastAPI()

# =========================
# SESSION
# =========================
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# =========================
# STATIC
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =========================
# PASSWORD
# =========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(password):
    return pwd_context.hash(password)

def get_current_user(request: Request):
    return request.session.get("user_id")

# =========================
# TELEGRAM BOT
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if TELEGRAM_TOKEN:
    bot = Bot(token=TELEGRAM_TOKEN)
    print("✅ Bot Telegram Ready")
else:
    bot = None
    print("❌ TELEGRAM TOKEN NOT FOUND")

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "alive 🚀"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

# =========================
# LOGIN
# =========================
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request):
    db = SessionLocal()
    form = await request.form()

    username = form.get("username")
    password = form.get("password")

    try:
        user = db.query(User).filter_by(username=username).first()

        if user and verify_password(password, user.password):
            request.session["user_id"] = user.id
            return RedirectResponse("/dashboard", status_code=302)

    finally:
        db.close()

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Login gagal"}
    )

# =========================
# LOGOUT
# =========================
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

# =========================
# CREATE ADMIN
# =========================
@app.get("/create-admin")
def create_admin():
    db = SessionLocal()

    try:
        existing = db.query(User).filter_by(username="admin").first()

        if existing:
            return {"msg": "Admin sudah ada"}

        user = User(
            username="admin",
            password=hash_password("admin123")
        )

        db.add(user)
        db.commit()

        return {"msg": "Admin created"}

    finally:
        db.close()

# =========================
# TELEGRAM WEBHOOK
# =========================
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        if "message" not in data:
            return {"ok": True}

        message = data["message"].get("text", "")
        user_id = data["message"]["chat"]["id"]

        result = await handle_message(str(user_id), message)

        if result and bot:
            await bot.send_message(chat_id=user_id, text=result["reply"])

        if bot:
            await bot.send_message(chat_id=user_id, text=result["reply"])

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}

# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
def dashboard(request: Request, status: str = None, q: str = None, page: int = 1):

    user_id = get_current_user(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user_id = int(user_id)

    db = SessionLocal()

    try:
        per_page = 10

        base_query = db.query(LeadDB).filter(LeadDB.owner_id == user_id)

        hot = base_query.filter(LeadDB.status == "HOT").count()
        warm = base_query.filter(LeadDB.status == "WARM").count()
        cold = base_query.filter(LeadDB.status == "COLD").count()

        query = base_query

        if status:
            query = query.filter(LeadDB.status == status)

        if q:
            query = query.filter(
                LeadDB.nama_orangtua.ilike(f"%{q}%") |
                LeadDB.whatsapp.ilike(f"%{q}%")
            )

        total = query.count()

        leads = query.order_by(LeadDB.created_at.desc()) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "leads": leads,
                "total": total,
                "page": page,
                "hot": hot,
                "warm": warm,
                "cold": cold
            }
        )

    finally:
        db.close()

# =========================
# SETTINGS PAGE
# =========================
@app.get("/settings")
def settings(request: Request):

    user_id = get_current_user(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user_id = str(user_id)

    db = SessionLocal()

    try:
        settings = db.query(BotSetting).filter(
            BotSetting.user_id == user_id
        ).all()

        return templates.TemplateResponse(
            "settings.html",
            {"request": request, "settings": settings}
        )

    finally:
        db.close()

# =========================
# TOGGLE BOT (FIXED + SAFE)
# =========================
class ToggleRequest(BaseModel):
    user_id: int
    status: bool

@app.post("/toggle-bot")
def toggle_bot(data: ToggleRequest):
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == data.user_id).first()

        if not user:
            return {"error": "User not found"}

        user.bot_active = data.status
        db.commit()

        # 🔥 CACHE UPDATE (FAST ACCESS)
        redis_client.set(f"bot:{data.user_id}", str(data.status))

        return {"success": True, "bot_active": data.status}

    finally:
        db.close()

# =========================
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    print("🚀 STARTUP INIT")

    Base.metadata.create_all(bind=engine)
    print("✅ DB ready")

    thread = threading.Thread(target=run_followup, daemon=True)
    thread.start()

    print("✅ Followup thread running")

print("✅ APP READY")