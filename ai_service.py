import json
import os
from openai import OpenAI
from database import SessionLocal
from models import LeadDB
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chat_memory = {}
MAX_HISTORY = 6

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
Kamu adalah CS profesional untuk bimbel anak baca tulis.

Gaya komunikasi:
- Ramah, sopan, natural seperti admin WhatsApp
- Gunakan emoji secukupnya (maks 2)

ATURAN:
- Maks 60 kata
- Maks 3–4 baris
- Gunakan line break
- Tidak bertele-tele

FUNNEL:
- COLD → edukasi
- WARM → arahkan trial
- HOT → closing

SAPAAN:
- CHAT_PERTAMA → boleh sapaan
- LANJUTAN → jangan sapaan terus

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
# GET USER
# =========================
def get_lead(user_id):
    db = SessionLocal()
    user = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()
    db.close()
    return user


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

    if any(x in msg for x in ["harga", "jadwal", "info", "berapa"]):
        return "WARM"

    return current_status


# =========================
# AUTO CLOSING
# =========================
def auto_closing(data, message, status):
    text = data.get("reply", "").lower()

    if status == "HOT":
        if "daftar" not in text:
            data["reply"] += "\n\nAku bantu daftarkan sekarang ya kak 😊"

    elif status == "WARM":
        if "trial" not in text:
            data["reply"] += "\n\nKita bisa coba trial dulu ya kak 😊"

    return data


# =========================
# OBJECTION HANDLING
# =========================
def handle_objection(message, reply):
    msg = message.lower()

    if "mahal" in msg:
        return (
            "Hehe paham kak 😊\n\n"
            "Biasanya orang tua ambil karena:\n"
            "• Anak cepat lancar baca\n"
            "• Lebih percaya diri\n\n"
            "Bisa coba trial dulu ya kak"
        )

    if any(x in msg for x in ["nanti", "belum", "pikir"]):
        return (
            "Siap kak 😊\n\n"
            "Biasanya mulai dari trial dulu biar lihat hasilnya\n\n"
            "Mau aku bantu cek jadwalnya?"
        )

    if any(x in msg for x in ["takut", "ga cocok"]):
        return (
            "Wajar kak 😊\n\n"
            "Makanya ada trial supaya anak bisa adaptasi\n\n"
            "Biasanya cepat nyaman kok"
        )

    return reply


# =========================
# ADVANCED CLOSING
# =========================
def advanced_closing(message, status, reply):
    msg = message.lower()

    # =========================
    # HOT → HARD CLOSE + URGENCY
    # =========================
    if status == "HOT":
        return (
            reply +
            "\n\nSlot minggu ini hampir penuh kak 😊\n"
            "Mau aku bantu amankan sekarang?"
        )

    # =========================
    # WARM → CHOICE CLOSING
    # =========================
    if status == "WARM":
        if any(x in msg for x in ["harga", "jadwal", "gimana", "info"]):
            return (
                reply +
                "\n\nKalau cocok, kakak lebih prefer:\n"
                "• Trial dulu\n"
                "• Atau langsung daftar?\n"
            )

    # =========================
    # COLD → MICRO COMMITMENT
    # =========================
    if status == "COLD":
        if "anak" in msg or "program" in msg:
            return (
                reply +
                "\n\nBiasanya kita mulai dari trial dulu biar anak nyaman 😊\n"
                "Mau aku bantu jadwalkan?"
            )

    return reply


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

    if user_id not in chat_memory:
        chat_memory[user_id] = []

    history = chat_memory[user_id]
    is_first_chat = len(history) == 0

    user = get_lead(user_id)

    nama = user.nama_orangtua if user else ""
    current_status = user.status if user else "COLD"

    history.append({
        "role": "user",
        "content": message
    })

    chat_memory[user_id] = history[-MAX_HISTORY:]

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
                *chat_memory[user_id]
            ],
            max_output_tokens=300
        )

        ai_text = response.output_text

    except Exception as e:
        print("❌ OPENAI ERROR:", e)
        return {
            "reply": "Maaf kak, lagi ada gangguan sebentar 🙏",
            "lead": {},
            "status": current_status
        }

    data = safe_parse(ai_text)

    if not data.get("lead"):
        data["lead"] = {}

    # =========================
    # STATUS UPDATE
    # =========================
    detected_status = detect_status(message, current_status)

    # jangan downgrade status
    status_priority = {"COLD": 1, "WARM": 2, "HOT": 3}

    if status_priority[detected_status] > status_priority[current_status]:
        data["status"] = detected_status
    else:
        data["status"] = current_status

    # =========================
    # RESPONSE PROCESS
    # =========================
    data = auto_closing(data, message, data["status"])
    data["reply"] = format_reply(data["reply"])
    data["reply"] = handle_objection(message, data["reply"])
    data["reply"] = advanced_closing(message, data.get("status", "COLD"), data["reply"])

    # =========================
    # SAVE
    # =========================
    save_lead(data, user_id)
    update_last_chat(user_id)

    history.append({
        "role": "assistant",
        "content": data["reply"]
    })

    return data


# =========================
# SAVE LEAD
# =========================
def save_lead(data, user_id):
    lead = data.get("lead", {})
    status = data.get("status", "COLD")

    db = SessionLocal()

    existing = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if existing:
        existing.status = status
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
            last_chat=datetime.utcnow()
        ))

    db.commit()
    db.close()