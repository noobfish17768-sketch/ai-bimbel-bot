import json
import os
from openai import OpenAI
from database.database import SessionLocal
from database.models import LeadDB, Conversation, BotSetting, User
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MAX_HISTORY = 6


# =========================
# BOT SETTING (OPTIONAL)
# =========================
def get_setting(user_id, key, default=None):
    db = SessionLocal()
    try:
        setting = db.query(BotSetting).filter_by(
            user_id=str(user_id),
            key=key
        ).first()

        return setting.value if setting else default
    finally:
        db.close()


# =========================
# SYSTEM PROMPT (DO NOT CHANGE)
# =========================
SYSTEM_PROMPT = """
Kamu adalah CS + Sales profesional untuk bimbel anak.

Gaya:
- Natural seperti WhatsApp
- Tidak robotik
- Maks 60 kata
- Maks 3–4 baris

Funnel:
- COLD → edukasi
- WARM → arahkan trial
- HOT → closing natural

ATURAN PENTING:
- Jangan ulang kalimat sebelumnya
- Jangan selalu closing
- Variasikan gaya komunikasi
- Jangan selalu pakai "Halo kak"
- Gunakan konteks chat sebelumnya

CLOSING:
- Lakukan hanya jika user sudah siap
- Variasikan:
  - "Mau aku bantu daftarkan?"
  - "Kita bisa mulai dari trial dulu"
  - "Mau aku cek jadwalnya?"
  - "Lebih nyaman trial atau langsung daftar?"

URGENCY:
- Hanya jika user HOT
- Jangan ulang "slot penuh"

OUTPUT JSON:
{
  "reply": "...",
  "lead": {
    "nama_orangtua": null,
    "nama_anak": null,
    "umur_anak": null,
    "whatsapp": null
  },
  "status": "COLD"
}
"""

# =========================
# HISTORY
# =========================
def load_history(user):
    if not user or not user.chat_history:
        return []
    try:
        return json.loads(user.chat_history)
    except:
        return []


def save_history(user, history):
    if not user:
        return
    user.chat_history = json.dumps(history[-MAX_HISTORY:])
    user.response_count = (user.response_count or 0) + 1


# =========================
# SAFE JSON PARSER
# =========================
def safe_parse(text):
    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}") + 1
        try:
            return json.loads(text[start:end])
        except:
            return {
                "reply": text,
                "lead": {},
                "status": "COLD"
            }


# =========================
# FORMAT
# =========================
def format_reply(text):
    if not text:
        return ""
    return "\n".join([l.strip() for l in text.split("\n")])


# =========================
# STATUS DETECTION
# =========================
def detect_status(message, current):
    msg = message.lower()

    if any(x in msg for x in ["daftar", "join", "ikut"]):
        return "HOT"
    if any(x in msg for x in ["harga", "jadwal", "info", "berapa"]):
        return "WARM"
    return current


# =========================
# SCORE
# =========================
def calculate_score(message, status, prev):
    score = prev or 0
    msg = message.lower()

    score += 5
    if status == "WARM":
        score += 15
    if status == "HOT":
        score += 30
    if any(x in msg for x in ["daftar", "mau", "join"]):
        score += 20

    return min(score, 100)


# =========================
# MAIN AI
# =========================
def run_ai(user_id: str, message: str, owner_id: int):

    db = SessionLocal()

    try:
        user_id = str(user_id)

        # =========================
        # BOT CONTROL (FIXED SAFE)
        # =========================
        owner = db.query(User).filter(User.id == owner_id).first()
        if owner and not owner.bot_active:
            return {
                "reply": "Admin sedang mematikan bot 🙏",
                "lead": {},
                "status": "COLD"
            }

        # =========================
        # GET LEAD
        # =========================
        lead = db.query(LeadDB).filter(
            LeadDB.whatsapp == user_id,
            LeadDB.owner_id == owner_id
        ).first()

        history = load_history(lead)

        nama = lead.nama_orangtua if lead else ""
        current_status = lead.status if lead else "COLD"
        prev_score = lead.lead_score if lead else 0

        history.append({"role": "user", "content": message})

        system_context = SYSTEM_PROMPT + f"""
KONDISI: {'CHAT_PERTAMA' if len(history) == 1 else 'LANJUTAN'}
NAMA_USER: {nama}
STATUS_LEAD: {current_status}
JUMLAH_CHAT: {len(history)}
LEAD_SCORE: {prev_score}
"""

        # =========================
        # AI CALL
        # =========================
        try:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": system_context},
                    *history[-MAX_HISTORY:]
                ],
                max_output_tokens=300
            )
            ai_text = response.output_text

        except Exception as e:
            print("AI ERROR:", e)
            return {
                "reply": "Maaf kak, lagi gangguan 🙏",
                "lead": {},
                "status": current_status
            }

        data = safe_parse(ai_text)

        new_status = detect_status(message, current_status)
        score = calculate_score(message, new_status, prev_score)
        reply = format_reply(data.get("reply", ""))

        # =========================
        # UPDATE LEAD
        # =========================
        if lead:
            lead.status = new_status
            lead.lead_score = score
            lead.last_chat = datetime.utcnow()
        else:
            lead = LeadDB(
                whatsapp=user_id,
                status=new_status,
                lead_score=score,
                last_chat=datetime.utcnow(),
                owner_id=owner_id
            )
            db.add(lead)
            db.flush()

        # =========================
        # SAVE CHAT
        # =========================
        db.add(Conversation(
            user_id=str(owner_id),
            external_id=user_id,
            message=message,
            response=reply,
            lead_id=lead.id,
            created_at=datetime.utcnow()
        ))

        history.append({"role": "assistant", "content": reply})
        save_history(lead, history)

        db.commit()

        return {
            "reply": reply,
            "status": new_status,
            "lead_score": score
        }

    except Exception as e:
        db.rollback()
        print("RUN_AI ERROR:", e)
        return {
            "reply": "Maaf kak, terjadi error 🙏",
            "status": "ERROR"
        }

    finally:
        db.close()