print("🚀 START APP")

from fastapi import FastAPI, Request
print("✅ Import FastAPI OK")

from fastapi.templating import Jinja2Templates
print("✅ Import Templates OK")

from database import engine, Base, SessionLocal
print("✅ Database OK")

from models import LeadDB
print("✅ Models OK")

from ai_service import run_ai
print("✅ AI Service OK")

import threading
from telegram_bot import run_bot

from fastapi.responses import RedirectResponse
from followup import run_followup
from sqlalchemy import or_
print("✅ Telegram Bot Import OK")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

print("📦 Create Table...")
Base.metadata.create_all(bind=engine)
print("✅ Table Ready")


# =========================
# API CHAT (TEST MANUAL)
# =========================
@app.post("/chat")
def chat(data: dict):
    print("\n🔥 /chat KE PANGGIL")
    print("DATA MASUK:", data)

    user_id = data.get("user_id", "user")
    message = data.get("message", "")

    print("USER:", user_id)
    print("MESSAGE:", message)

    result = run_ai(user_id, message)

    print("AI RESULT:", result)

    return result


# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
def dashboard(request: Request, status: str = None, q: str = None):
    print("\n📊 DASHBOARD DI BUKA")

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

    print("JUMLAH LEADS:", len(leads))
    print("TYPE REQ:", type(request))

    # 🔥 convert ke dict (biar Jinja ga error)
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
# MAIN RUNNER
# =========================
if __name__ == "__main__":
    print("\n🤖 START TELEGRAM BOT THREAD...")
    threading.Thread(target=run_bot).start()
    threading.Thread(target=run_followup).start()

    print("🌐 START FASTAPI...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/update-status/{lead_id}/{status}")
def update_status(lead_id: int, status: str):
    db = SessionLocal()

    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()

    if lead:
        lead.status = status.upper()
        db.commit()

    db.close()

    return RedirectResponse(url="/dashboard", status_code=302)