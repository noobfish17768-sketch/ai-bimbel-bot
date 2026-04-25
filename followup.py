import time
from datetime import datetime, timedelta
from database import SessionLocal
from models import LeadDB
from telegram import Bot
import os

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

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
# GENERATE PESAN FOLLOWUP (AI STYLE)
# =========================
def generate_followup(lead):

    nama = lead.nama_orangtua or "kak"
    status = lead.status
    score = getattr(lead, "lead_score", 0)

    # =========================
    # HOT → HARD CLOSE
    # =========================
    if score > 85:
        return f"""Kak {nama}, aku bantu ringkas ya 😊

Biasanya orang tua ambil karena anak jadi lebih cepat lancar baca

Kalau kakak sudah cocok, aku bisa bantu proses daftarnya sekarang"""

    # =========================
    # WARM → TRIAL PUSH
    # =========================
    if score > 60:
        return f"""Kak {nama}, biasanya orang tua mulai dari trial dulu 😊

Dari situ bisa lihat perkembangan anaknya langsung

Mau aku bantu cek jadwal trial yang tersedia?"""

    # =========================
    # MEDIUM → EDUKASI
    # =========================
    if score > 30:
        return f"""Kak {nama}, program ini fokus bantu anak:

• Lebih cepat membaca  
• Lebih percaya diri  

Biasanya perubahan sudah mulai terlihat dalam beberapa pertemuan 😊"""

    # =========================
    # LOW → SOFT TOUCH
    # =========================
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
# ANTI SPAM (MAX 3 FOLLOWUP)
# =========================
def can_send_again(lead):
    count = getattr(lead, "followup_count", 0)
    return count < 3


# =========================
# MAIN LOOP
# =========================
def run_followup():
    print("🚀 AI FOLLOWUP SYSTEM START")

    while True:
        db = SessionLocal()
        leads = db.query(LeadDB).all()

        for lead in leads:
            try:
                if not lead.whatsapp:
                    continue

                if not can_send_again(lead):
                    continue

                if should_followup(lead):

                    msg = generate_followup(lead)

                    print(f"📤 FOLLOWUP KE {lead.whatsapp} | SCORE: {getattr(lead,'lead_score',0)}")

                    bot.send_message(
                        chat_id=lead.whatsapp,
                        text=msg
                    )

                    # update DB
                    lead.last_followup = datetime.utcnow()

                    if hasattr(lead, "followup_count"):
                        lead.followup_count += 1

                    db.commit()

            except Exception as e:
                print("❌ ERROR FOLLOWUP:", e)

        db.close()
        time.sleep(60)