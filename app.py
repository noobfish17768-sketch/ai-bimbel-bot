print("🚀 START APP")

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database import engine, Base, SessionLocal
from models import LeadDB
from ai_service import run_ai

from sqlalchemy import or_

from telegram import Bot
import os
import asyncio
import threading

from followup import run_followup

print("✅ Import OK")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =========================
# INIT TELEGRAM BOT
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM TOKEN TIDAK ADA!")
    bot = None
else:
    bot = Bot(token=TELEGRAM_TOKEN)
    print("✅ Bot Telegram Ready")

# =========================
# INIT DATABASE
# =========================
print("📦 Create Table...")
Base.metadata.create_all(bind=engine)
print("✅ Table Ready")


# =========================
# ROOT (HEALTH CHECK)
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
        print("🔥 WEBHOOK MASUK:", data)

        if "message" not in data:
            print("⚠️ Bukan message update")
            return {"ok": True}

        message = data["message"].get("text", "")
        user_id = data["message"]["chat"]["id"]

        print(f"👤 USER: {user_id}")
        print(f"💬 MSG: {message}")

        # 🔥 run AI di thread (biar ga blocking)
        result = await asyncio.to_thread(run_ai, str(user_id), message)

        print("🤖 AI RESULT:", result)

        # =========================
        # SEND MESSAGE
        # =========================
        if bot:
            await bot.send_message(
                chat_id=user_id,
                text=result["reply"]
            )
            print("✅ Pesan terkirim")
        else:
            print("❌ Bot tidak aktif")

        return {"ok": True}

    except Exception as e:
        print("❌ ERROR WEBHOOK:", e)
        return {"ok": True}


# =========================
# API CHAT (TEST MANUAL)
# =========================
@app.post("/chat")
def chat(data: dict):
    user_id = data.get("user_id", "user")
    message = data.get("message", "")

    result = run_ai(user_id, message)
    return result


# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
def dashboard(request: Request, status: str = None, q: str = None):
    db = SessionLocal()
    query = db.query(LeadDB)

    if status:
        query = query.filter(LeadDB.status == status)

    if q:
        query = query.filter(
            or_(
                LeadDB.nama_orangtua.contains(q),
                LeadDB.whatsapp.contains(q)
            )
        )

    leads = query.all()
    db.close()

    leads_data = []
    for l in leads:
        leads_data.append({
            "nama_orangtua": l.nama_orangtua,
            "nama_anak": l.nama_anak,
            "umur_anak": l.umur_anak,
            "whatsapp": l.whatsapp,
            "status": l.status
        })

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"leads": leads_data}
    )


# =========================
# UPDATE STATUS
# =========================
@app.get("/update-status/{lead_id}/{status}")
def update_status(lead_id: int, status: str):
    db = SessionLocal()

    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()

    if lead:
        lead.status = status.upper()
        db.commit()

    db.close()

    return RedirectResponse(url="/dashboard", status_code=302)


# =========================
# START BACKGROUND JOB
# =========================
@app.on_event("startup")
def start_background_jobs():
    print("🚀 START BACKGROUND JOBS")

    try:
        thread = threading.Thread(target=run_followup, daemon=True)
        thread.start()
        print("✅ Follow-up system jalan")
    except Exception as e:
        print("❌ Gagal start followup:", e)

print("✅ App siap jalan")