import json
import os
from openai import OpenAI
from database import SessionLocal
from models import LeadDB
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_HISTORY = 6

# =========================
# SYSTEM PROMPT
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
- WARM → trial
- HOT → closing

Aturan:
- Jangan ulang kalimat
- Jangan selalu closing
- Variasikan gaya

Output JSON:
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
# GET USER + HISTORY
# =========================
def get_lead(user_id):
    db = SessionLocal()
    user = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()
    db.close()
    return user


def load_history(user):
    if not user or not user.chat_history:
        return []

    try:
        return json.loads(user.chat_history)
    except:
        return []


def save_history(user_id, history):
    db = SessionLocal()
    user = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if user:
        user.chat_history = json.dumps(history[-MAX_HISTORY:])
        user.response_count += 1
        db.commit()

    db.close()


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
        return text

    lines = text.strip().split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            cleaned.append("")
            continue

        if not line.startswith(("•", "-", "📚")):
            line = line[:1].upper() + line[1:]

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# STATUS DETECTION
# =========================
def detect_status(message, current_status):
    msg = message.lower()

    if any(x in msg for x in ["daftar", "join", "ikut"]):
        return "HOT"

    if any(x in msg for x in ["harga", "jadwal", "info"]):
        return "WARM"

    return current_status


# =========================
# SCORING
# =========================
def calculate_score(message, status, prev_score):
    msg = message.lower()
    score = prev_score or 0

    score += 5

    if status == "WARM":
        score += 15

    if status == "HOT":
        score += 30

    if any(x in msg for x in ["daftar", "mau", "join"]):
        score += 20

    return min(score, 100)


# =========================
# UPDATE LAST CHAT
# =========================
def update_last_chat(user_id):
    db = SessionLocal()

    user = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if user:
        user.last_chat = datetime.utcnow()
        db.commit()

    db.close()


# =========================
# MAIN AI
# =========================
def run_ai(user_id: str, message: str):

    user = get_lead(user_id)

    history = load_history(user)
    is_first_chat = len(history) == 0

    nama = user.nama_orangtua if user else ""
    current_status = user.status if user else "COLD"
    prev_score = user.lead_score if user else 0

    # append user msg
    history.append({
        "role": "user",
        "content": message
    })

    system_context = SYSTEM_PROMPT + f"""

KONDISI: {'CHAT_PERTAMA' if is_first_chat else 'LANJUTAN'}
NAMA_USER: {nama}
STATUS_LEAD: {current_status}
"""

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
        print("❌ AI ERROR:", e)
        return {
            "reply": "Maaf kak, lagi gangguan 🙏",
            "lead": {},
            "status": current_status
        }

    data = safe_parse(ai_text)

    if not data.get("lead"):
        data["lead"] = {}

    # =========================
    # STATUS UPDATE
    # =========================
    detected = detect_status(message, current_status)

    priority = {"COLD": 1, "WARM": 2, "HOT": 3}

    if priority[detected] > priority[current_status]:
        data["status"] = detected
    else:
        data["status"] = current_status

    # =========================
    # SCORING
    # =========================
    score = calculate_score(message, data["status"], prev_score)
    data["lead_score"] = score

    # =========================
    # FORMAT
    # =========================
    data["reply"] = format_reply(data["reply"])

    # =========================
    # SAVE DB
    # =========================
    save_lead(data, user_id)
    update_last_chat(user_id)

    # append assistant
    history.append({
        "role": "assistant",
        "content": data["reply"]
    })

    save_history(user_id, history)

    return data


# =========================
# SAVE LEAD
# =========================
def save_lead(data, user_id):
    lead = data.get("lead", {})
    status = data.get("status", "COLD")
    score = data.get("lead_score", 0)

    db = SessionLocal()

    existing = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if existing:
        existing.status = status
        existing.lead_score = score
        existing.last_chat = datetime.utcnow()

        if lead.get("nama_orangtua"):
            existing.nama_orangtua = lead["nama_orangtua"]

        if lead.get("nama_anak"):
            existing.nama_anak = lead["nama_anak"]

        if lead.get("umur_anak"):
            existing.umur_anak = lead["umur_anak"]

    else:
        db.add(LeadDB(
            whatsapp=user_id,
            nama_orangtua=lead.get("nama_orangtua"),
            nama_anak=lead.get("nama_anak"),
            umur_anak=lead.get("umur_anak"),
            status=status,
            lead_score=score,
            last_chat=datetime.utcnow()
        ))

    db.commit()
    db.close()