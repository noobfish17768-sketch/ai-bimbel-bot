print("🚀 START APP")

import os
import asyncio
import threading

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from telegram import Bot

from database import engine, Base, SessionLocal
from models import LeadDB
from ai_service import run_ai
from followup import run_followup

print("✅ Import OK")

app = FastAPI()
templates = Jinja2Templates(directory="templates")


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
# TELEGRAM WEBHOOK
# =========================
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("🔥 WEBHOOK:", data)

        if "message" not in data:
            return {"ok": True}

        message = data["message"].get("text", "")
        user_id = data["message"]["chat"]["id"]

        print(f"👤 {user_id} | 💬 {message}")

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
# DASHBOARD (FIXED)
# =========================
@app.get("/dashboard")
def dashboard(request: Request, status: str = None, q: str = None):
    db = SessionLocal()

    try:
        print("🔥 DASHBOARD HIT")

        leads = db.query(LeadDB).all()

        print("🔥 RAW LEADS:", leads)

        leads_data = []

        for l in leads:
            print("ROW:", l)

            leads_data.append({
                "id": l.id,
                "nama_orangtua": l.nama_orangtua,
                "nama_anak": l.nama_anak,
                "umur_anak": l.umur_anak,
                "whatsapp": l.whatsapp,
                "status": l.status
            })

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "leads": leads_data
            }
        )

    except Exception as e:
        print("🔥 ERROR DASHBOARD:", repr(e))
        return {"error": str(e)}

    finally:
        db.close()


# =========================
# UPDATE STATUS
# =========================
@app.get("/update-status/{lead_id}/{status}")
def update_status(lead_id: int, status: str):
    db = SessionLocal()

    try:
        lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()

        if lead:
            lead.status = status.upper()
            db.commit()

    except Exception as e:
        print("❌ UPDATE STATUS ERROR:", e)
        db.rollback()

    finally:
        db.close()

    return RedirectResponse("/dashboard", status_code=302)


# =========================
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    print("🚀 STARTUP INIT")

    # init DB
    Base.metadata.create_all(bind=engine)
    print("✅ DB initialized")

    # start followup thread
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