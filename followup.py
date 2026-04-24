import time
import os
from datetime import datetime, timedelta
from database import SessionLocal
from models import LeadDB
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ TELEGRAM TOKEN TIDAK ADA (FOLLOWUP)")
    bot = None
else:
    bot = Bot(token=TOKEN)
    print("✅ FOLLOWUP BOT READY")


def get_followup_message(status):
    if status == "COLD":
        return """Kak, tadi sempat tanya soal program ya 😊

Kalau boleh tahu, anaknya lagi fokus membaca atau menulis?"""

    elif status == "WARM":
        return """Programnya cocok banget buat usia anak kak 📚

Kita bisa mulai dari trial dulu biar lihat hasilnya

Mau aku bantu atur jadwalnya?"""

    elif status == "HOT":
        return """Slot minggu ini hampir penuh kak 😊

Kalau mau, aku bantu amankan tempatnya sekarang ya"""

    return None


def should_followup(lead):
    now = datetime.utcnow()

    if not lead.last_chat:
        return False

    delay_map = {
        "COLD": 10,
        "WARM": 60,
        "HOT": 180
    }

    delay = delay_map.get(lead.status, 60)
    last_time = lead.last_followup or lead.last_chat

    return now - last_time > timedelta(minutes=delay)


def run_followup():
    print("🚀 FOLLOWUP SYSTEM START")

    while True:
        db = SessionLocal()

        try:
            leads = db.query(LeadDB).all()

            for lead in leads:
                try:
                    if not bot:
                        continue

                    if not lead.whatsapp:
                        continue

                    if should_followup(lead):
                        msg = get_followup_message(lead.status)

                        if msg:
                            print(f"📤 FOLLOWUP KE {lead.whatsapp}")

                            bot.send_message(
                                chat_id=lead.whatsapp,
                                text=msg
                            )

                            lead.last_followup = datetime.utcnow()
                            db.commit()

                except Exception as e:
                    print("❌ ERROR FOLLOWUP USER:", e)

        except Exception as e:
            print("❌ ERROR DB FOLLOWUP:", e)

        finally:
            db.close()

        time.sleep(60)