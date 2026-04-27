import json
import os
from openai import OpenAI
from database import SessionLocal
from models import LeadDB, Conversation, BotSetting
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_HISTORY = 6


# =========================
# ⚙️ BOT SETTING
# =========================
def get_setting(key, default=None):
    db = SessionLocal()
    try:
        setting = db.query(BotSetting).filter_by(key=key).first()
        return setting.value if setting else default
    finally:
        db.close()


# =========================
# SYSTEM PROMPT (TIDAK DIUBAH)
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
    if user:
        user.chat_history = json.dumps(history[-MAX_HISTORY:])
        user.response_count = (user.response_count or 0) + 1


# =========================
# SAFE JSON
# =========================
def safe_parse(ai_text):
    try:
        return json.loads(ai_text)
    except:
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1
        if start != -1 and end != -1:
            try:
                return json.loads(ai_text[start:end])
            except:
                pass

    return {
        "reply": ai_text,
        "lead": {},
        "status": "COLD"
    }


# =========================
# FORMAT
# =========================
def format_reply(text):
    if not text:
        return ""
    lines = text.strip().split("\n")
    return "\n".join([l.strip() for l in lines])


# =========================
# STATUS
# =========================
def detect_status(message, current_status):
    msg = message.lower()

    if any(x in msg for x in ["daftar", "join", "ikut"]):
        return "HOT"

    if any(x in msg for x in ["harga", "jadwal", "info", "berapa"]):
        return "WARM"

    return current_status


# =========================
# SCORE
# =========================
def calculate_score(message, status, prev_score):
    score = prev_score or 0
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
# MAIN AI (🔥 FIXED)
# =========================
def run_ai(user_id: str, message: str, owner_id: int = 1):

    # 🔥 BOT CONTROL
    bot_status = get_setting("bot_status", "ON")

    if bot_status == "OFF":
        return {
            "reply": "Admin sedang mematikan bot 🙏",
            "lead": {},
            "status": "COLD"
        }

    db = SessionLocal()

    try:
        user_id = str(user_id)

        # =========================
        # GET LEAD
        # =========================
        user = db.query(LeadDB).filter(
            LeadDB.whatsapp == user_id
        ).first()

        history = load_history(user)

        nama = user.nama_orangtua if user else ""
        current_status = user.status if user else "COLD"
        prev_score = user.lead_score if user else 0

        # =========================
        # USER MESSAGE
        # =========================
        history.append({
            "role": "user",
            "content": message
        })

        # =========================
        # CONTEXT
        # =========================
        system_context = SYSTEM_PROMPT + f"""

KONDISI: {'CHAT_PERTAMA' if len(history) == 1 else 'LANJUTAN'}
NAMA_USER: {nama}
STATUS_LEAD: {current_status}
JUMLAH_CHAT: {len(history)}
LAST_ACTIVITY: {user.last_chat if user else "NONE"}
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
        # UPDATE / CREATE LEAD
        # =========================
        if user:
            user.status = new_status
            user.lead_score = score
            user.last_chat = datetime.utcnow()
        else:
            user = LeadDB(
                whatsapp=user_id,
                status=new_status,
                lead_score=score,
                last_chat=datetime.utcnow(),
                owner_id=owner_id
            )
            db.add(user)
            db.flush()

        # =========================
        # SAVE CONVERSATION (🔥 FIX)
        # =========================
        chat = Conversation(
            user_id=str(owner_id),   # dashboard user
            external_id=user_id,     # 🔥 Telegram ID
            message=message,
            response=reply,
            lead_id=user.id,
            created_at=datetime.utcnow()
        )

        db.add(chat)

        # =========================
        # SAVE HISTORY
        # =========================
        history.append({
            "role": "assistant",
            "content": reply
        })

        save_history(user, history)

        db.commit()

        return {
            "reply": reply,
            "status": new_status,
            "lead_score": score
        }

    except Exception as e:
        db.rollback()
        print("❌ RUN_AI ERROR:", e)

        return {
            "reply": "Maaf kak, terjadi error 🙏",
            "lead": {},
            "status": "ERROR"
        }

    finally:
        db.close()