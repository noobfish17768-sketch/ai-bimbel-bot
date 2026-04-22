import time
from datetime import datetime, timedelta
from database import SessionLocal
from models import LeadDB
from whatsapp import send_whatsapp

def run_followup():
    while True:
        db = SessionLocal()

        users = db.query(LeadDB).all()

        for u in users:
            if not u.last_chat:
                continue

            if datetime.utcnow() - u.last_chat > timedelta(hours=1):
                send_whatsapp(
                    u.whatsapp,
                    "Halo kak 😊\n\nMasih ingin tanya soal programnya?"
                )

        db.close()
        time.sleep(60)