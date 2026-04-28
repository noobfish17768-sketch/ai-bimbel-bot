import time
from datetime import datetime, timedelta

from database.database import SessionLocal
from database.models import LeadDB
from telegram import Bot
import os

# =========================
# TELEGRAM INIT SAFE
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


# =========================
# DELAY RULE
# =========================
def get_delay(score: int) -> int:
    if score < 30:
        return 360   # 6 jam
    elif score < 60:
        return 120   # 2 jam
    elif score < 85:
        return 45    # 45 menit
    return 15       # HOT


# =========================
# MESSAGE TEMPLATE
# =========================
def generate_followup(lead):
    nama = lead.nama_orangtua or "kak"
    score = lead.lead_score or 0

    if score > 85:
        return f"""Kak {nama}, aku bantu ringkas ya 😊

Banyak orang tua ambil program ini karena anak jadi lebih cepat lancar membaca.

Kalau kakak mau, aku bisa bantu proses daftarnya sekarang."""

    if score > 60:
        return f"""Kak {nama}, biasanya orang tua mulai dari trial dulu 😊

Dari situ bisa lihat perkembangan anaknya langsung.

Mau aku cek jadwal trial yang tersedia?"""

    if score > 30:
        return f"""Kak {nama}, program ini bantu anak:

• Lebih cepat membaca  
• Lebih percaya diri  

Biasanya sudah terlihat hasilnya dalam beberapa pertemuan 😊"""

    return f"""Kak {nama}, tadi sempat tanya ya 😊

Kalau boleh tahu, anaknya sekarang lagi belajar membaca atau menulis?"""


# =========================
# CHECK ELIGIBILITY
# =========================
def should_followup(lead) -> bool:
    if not lead.last_chat:
        return False

    now = datetime.utcnow()
    last_time = lead.last_followup or lead.last_chat

    delay = get_delay(lead.lead_score or 0)

    return (now - last_time) > timedelta(minutes=delay)


def can_send(lead) -> bool:
    return (lead.followup_count or 0) < 3


# =========================
# MAIN WORKER LOOP
# =========================
def run_followup():
    print("🚀 FOLLOWUP SYSTEM STARTED")

    if not bot:
        print("❌ TELEGRAM TOKEN NOT FOUND")
        return

    while True:
        db = SessionLocal()

        try:
            leads = db.query(LeadDB).all()

            for lead in leads:
                try:
                    # =========================
                    # VALIDATION
                    # =========================
                    if not lead.telegram_id:
                        continue

                    if not can_send(lead):
                        continue

                    if not should_followup(lead):
                        continue

                    # =========================
                    # MESSAGE
                    # =========================
                    msg = generate_followup(lead)

                    print(f"📤 SEND FOLLOWUP -> {lead.telegram_id} | SCORE {lead.lead_score}")

                    bot.send_message(
                        chat_id=lead.telegram_id,
                        text=msg
                    )

                    # =========================
                    # UPDATE SAFE
                    # =========================
                    lead.followup_count = (lead.followup_count or 0) + 1
                    lead.last_followup = datetime.utcnow()

                    db.commit()

                except Exception as e:
                    print(f"❌ ERROR LEAD {lead.id}: {e}")
                    db.rollback()

        except Exception as e:
            print("❌ FOLLOWUP LOOP ERROR:", e)

        finally:
            db.close()

        time.sleep(60)