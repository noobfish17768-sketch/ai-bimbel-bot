import time
from datetime import datetime, timedelta
from database import SessionLocal
from models import LeadDB
from telegram import Bot
import os

# =========================
# SAFE BOT INIT
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


# =========================
# HITUNG DELAY BERDASARKAN SCORE
# =========================
def get_delay(score):
    if score < 30:
        return 360  # 6 jam
    elif score < 60:
        return 120  # 2 jam
    elif score < 85:
        return 45   # 45 menit
    else:
        return 15   # 15 menit


# =========================
# GENERATE PESAN FOLLOWUP
# =========================
def generate_followup(lead):
    nama = lead.nama_orangtua or "kak"
    score = getattr(lead, "lead_score", 0)

    if score > 85:
        return f"""Kak {nama}, aku bantu ringkas ya 😊

Biasanya orang tua ambil karena anak jadi lebih cepat lancar baca

Kalau kakak sudah cocok, aku bisa bantu proses daftarnya sekarang"""

    if score > 60:
        return f"""Kak {nama}, biasanya orang tua mulai dari trial dulu 😊

Dari situ bisa lihat perkembangan anaknya langsung

Mau aku bantu cek jadwal trial yang tersedia?"""

    if score > 30:
        return f"""Kak {nama}, program ini fokus bantu anak:

• Lebih cepat membaca  
• Lebih percaya diri  

Biasanya perubahan sudah mulai terlihat dalam beberapa pertemuan 😊"""

    return f"""Kak {nama}, tadi sempat tanya ya 😊

Kalau boleh tahu, anaknya sekarang lagi belajar membaca atau menulis?"""


# =========================
# CEK PERLU FOLLOWUP
# =========================
def should_followup(lead):
    now = datetime.utcnow()

    if not lead.last_chat:
        return False

    score = getattr(lead, "lead_score", 0)
    delay_minutes = get_delay(score)

    last_time = lead.last_followup or lead.last_chat

    return now - last_time > timedelta(minutes=delay_minutes)


# =========================
# ANTI SPAM
# =========================
def can_send_again(lead):
    return (lead.followup_count or 0) < 3


# =========================
# MAIN LOOP (SAFE VERSION)
# =========================
def run_followup():
    print("🚀 AI FOLLOWUP SYSTEM START")

    if not bot:
        print("❌ TELEGRAM BOT NOT INITIALIZED")
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

                    if not can_send_again(lead):
                        continue

                    if not should_followup(lead):
                        continue

                    # =========================
                    # SEND MESSAGE
                    # =========================
                    msg = generate_followup(lead)

                    print(f"📤 FOLLOWUP KE {lead.telegram_id} | SCORE: {getattr(lead,'lead_score',0)}")

                    bot.send_message(
                        chat_id=lead.telegram_id,
                        text=msg
                    )

                    # =========================
                    # UPDATE DB SAFE
                    # =========================
                    lead.last_followup = datetime.utcnow()
                    lead.followup_count = (lead.followup_count or 0) + 1

                    db.commit()

                except Exception as e:
                    print(f"❌ ERROR PER LEAD {lead.id}: {e}")
                    db.rollback()

        except Exception as e:
            print("❌ FATAL FOLLOWUP ERROR:", e)

        finally:
            db.close()

        time.sleep(60)