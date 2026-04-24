import time
from datetime import datetime, timedelta
from database import SessionLocal
from models import LeadDB
from telegram import Bot
import os

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

def run_followup():
    print("🔥 FOLLOW UP JALAN...")

    while True:
        db = SessionLocal()

        now = datetime.utcnow()

        leads = db.query(LeadDB).all()

        for lead in leads:
            if not lead.last_chat:
                continue

            diff = now - lead.last_chat

            # =========================
            # 10 MENIT
            # =========================
            if timedelta(minutes=10) < diff < timedelta(minutes=11):
                send_message(lead.whatsapp,
                    "Halo kak 😊\nMasih mau tanya-tanya soal programnya?"
                )

            # =========================
            # 1 JAM
            # =========================
            elif timedelta(hours=1) < diff < timedelta(hours=1, minutes=5):
                send_message(lead.whatsapp,
                    "Kak, kebetulan slot trial minggu ini terbatas 📚\nMau aku bantu cek jadwalnya?"
                )

            # =========================
            # 1 HARI
            # =========================
            elif timedelta(days=1) < diff < timedelta(days=1, minutes=5):
                send_message(lead.whatsapp,
                    "Kak 😊\nProgram ini cocok banget buat anak yang baru mulai baca\n\nKalau mau, kita bisa coba trial dulu ya"
                )

        db.close()
        time.sleep(60)


def send_message(user_id, text):
    try:
        bot.send_message(
            chat_id=user_id,
            text=text
        )
        print("📤 FOLLOW UP:", user_id)
    except Exception as e:
        print("❌ ERROR FOLLOW UP:", e)