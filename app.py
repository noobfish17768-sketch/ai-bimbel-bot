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

print("✅ Import OK")

app = FastAPI()
templates = Jinja2Templates(directory="templates")
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

# =========================
# INIT DATABASE
# =========================
print("📦 Create Table...")
Base.metadata.create_all(bind=engine)
print("✅ Table Ready")


# =========================
# TELEGRAM WEBHOOK
# =========================
@app.get("/")
def root():
    return {"status": "hidup"}
print("✅ Hidup")

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("🔥 WEBHOOK MASUK:", data)

        if "message" not in data:
            print("❌ BUKAN MESSAGE")
            return {"ok": True}

        message = data["message"].get("text", "")
        user_id = data["message"]["chat"]["id"]

        print("👤 USER:", user_id)
        print("💬 MSG:", message)

        import asyncio
        result = await asyncio.to_thread(run_ai, str(user_id), message)

        print("🤖 AI RESULT:", result)

        await bot.send_message(
            chat_id=user_id,
            text=result["reply"]
        )

        print("✅ PESAN TERKIRIM")

        return {"ok": True}

    except Exception as e:
        print("❌ ERROR BESAR:", e)
        return {"ok": True}

# =========================
# API CHAT (TEST)
# =========================
@app.post("/chat")
def chat(data: dict):
    user_id = data.get("user_id", "user")
    message = data.get("message", "")

    result = run_ai(user_id, message)
    return result
print("✅ API Jalan")

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
print("✅ Dashboard Siap")

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
print("✅ Update Status Ada")
print("✅ App Siap Jalan")