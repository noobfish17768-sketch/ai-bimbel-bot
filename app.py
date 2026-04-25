print("🚀 START APP")

import os
import asyncio
import threading

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from passlib.context import CryptContext

from telegram import Bot

from database import engine, Base, SessionLocal
from models import LeadDB, Conversation, BotSetting, User
from ai_service import run_ai
from followup import run_followup

print("✅ Import OK")

app = FastAPI()

# =========================
# SESSION
# =========================
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# =========================
# STATIC FILES
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# =========================
# PASSWORD HASH
# =========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def hash_password(password):
    return pwd_context.hash(password)


def get_current_user(request: Request):
    return request.session.get("user_id")


# =========================
# TELEGRAM BOT INIT
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM TOKEN TIDAK ADA!")
    bot = None
else:
    bot = Bot(token=TELEGRAM_TOKEN)
    print("✅ Bot Telegram Ready")


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "hidup 🚀"}


# =========================
# 🔐 LOGIN PAGE
# =========================
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request
        },
        request=request   # 🔥 WAJIB DI VERSI BARU
    )


# =========================
# 🔐 LOGIN PROCESS
# =========================
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
        request,
        "login.html",
        {"request": request}
    )


# =========================
# 🔐 LOGOUT
# =========================
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# =========================
# 👤 CREATE ADMIN
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

        return {"msg": "Admin berhasil dibuat"}

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

        print(f"👤 {user_id} | 💬 {message}")

        # ⚠️ sementara owner_id = 1 (admin default)
        result = await asyncio.to_thread(run_ai, str(user_id), message)

        if bot:
            await bot.send_message(
                chat_id=user_id,
                text=result["reply"]
            )

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"ok": True}


# =========================
# CHAT TEST
# =========================
@app.post("/chat")
def chat(data: dict):
    user_id = data.get("user_id", "user")
    message = data.get("message", "")

    return run_ai(user_id, message)


# =========================
# 📊 DASHBOARD (MULTI TENANT)
# =========================
@app.get("/dashboard")
def dashboard(request: Request, status: str = None, q: str = None, page: int = 1):

    user_id = get_current_user(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()

    try:
        per_page = 10

        # 🔥 FILTER OWNER
        query = db.query(LeadDB).filter(LeadDB.owner_id == user_id)

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
                "page": page
            }
        )

    finally:
        db.close()


# =========================
# 💬 CONVERSATIONS (FILTER OWNER)
# =========================
@app.get("/conversations")
def conversations(request: Request):

    user_id = get_current_user(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()

    try:
        chats = db.query(Conversation) \
            .join(LeadDB, Conversation.lead_id == LeadDB.id) \
            .filter(LeadDB.owner_id == user_id) \
            .order_by(Conversation.created_at.desc()) \
            .limit(50) \
            .all()

        return templates.TemplateResponse(
            "conversations.html",
            {
                "request": request,
                "chats": chats
            }
        )

    finally:
        db.close()


# =========================
# ⚙️ SETTINGS
# =========================
@app.get("/settings")
def settings(request: Request):

    if not get_current_user(request):
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()

    try:
        settings = db.query(BotSetting).all()

        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "settings": settings
            }
        )

    finally:
        db.close()


@app.post("/settings")
async def update_settings(request: Request):

    if not get_current_user(request):
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()

    form = await request.form()
    key = form.get("key")
    value = form.get("value")

    try:
        setting = db.query(BotSetting).filter_by(key=key).first()

        if setting:
            setting.value = value
        else:
            db.add(BotSetting(key=key, value=value))

        db.commit()

    except Exception as e:
        print("❌ SETTINGS ERROR:", e)
        db.rollback()

    finally:
        db.close()

    return RedirectResponse("/settings", status_code=302)


# =========================
# UPDATE STATUS (SECURE)
# =========================
@app.get("/update-status/{lead_id}/{status}")
def update_status(request: Request, lead_id: int, status: str):

    user_id = get_current_user(request)

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()

    try:
        lead = db.query(LeadDB).filter(
            LeadDB.id == lead_id,
            LeadDB.owner_id == user_id
        ).first()

        if lead:
            lead.status = status.upper()
            db.commit()

    finally:
        db.close()

    return RedirectResponse("/dashboard", status_code=302)


# =========================
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    print("🚀 STARTUP INIT")

    Base.metadata.create_all(bind=engine)
    print("✅ DB initialized")

    try:
        thread = threading.Thread(
            target=run_followup,
            daemon=True
        )
        thread.start()

        print("✅ Follow-up thread started")

    except Exception as e:
        print("❌ Followup error:", e)


print("✅ APP READY")