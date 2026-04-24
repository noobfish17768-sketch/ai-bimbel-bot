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

SYSTEM_PROMPT = """
Kamu adalah CS profesional untuk bimbel anak baca tulis.

Gaya komunikasi:
- Ramah, sopan, natural seperti admin WhatsApp
- Tidak kaku dan tidak seperti robot
- Gunakan emoji secukupnya (maksimal 2, contoh: 😊📚)

ATURAN WAJIB:
- Gunakan bahasa Indonesia sesuai EYD
- Gunakan sentence case
- Gunakan line break (\\n) agar mudah dibaca di WhatsApp
- Maksimal 60 kata
- Maksimal 3–4 baris utama
- Hindari kalimat bertele-tele

FORMAT BALASAN:
1. Sapaan singkat (hanya jika perlu)
2. Jawaban inti
3. (Opsional) bullet point max 2
4. Tutup dengan 1 pertanyaan (tidak wajib selalu)

TUJUAN:
- Mengarahkan ke pendaftaran
- Mengumpulkan data user

ATURAN SAPAAN:
- Jika KONDISI = CHAT_PERTAMA → boleh pakai "Halo kak 😊"
- Jika LANJUTAN → jangan pakai sapaan pembuka
- Variasikan: "Baik kak", "Siap kak", atau langsung jawab

PERSONALISASI:
- Gunakan NAMA_USER jika ada (sesekali saja)

STRATEGI STATUS:
- COLD → edukasi
- WARM → arahkan trial
- HOT → closing langsung

OUTPUT WAJIB JSON:
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
# SAFE JSON PARSER
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
# FORMAT WHATSAPP
# =========================
def format_reply(text: str):
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
# AUTO CLOSING
# =========================
def auto_closing(data, message, status):
    text = data.get("reply", "")
    msg = message.lower()

    # =========================
    # HOT → HARD CLOSING
    # =========================
    if status == "HOT":
        if "daftar" not in text.lower():
            text += "\n\nBoleh aku bantu daftarkan sekarang kak? 😊"

    # =========================
    # WARM → SOFT CLOSING
    # =========================
    elif status == "WARM":
        if any(x in msg for x in ["harga", "jadwal", "berapa"]):
            text += "\n\nKalau cocok, kita bisa coba trial dulu ya kak 😊"

    # =========================
    # COLD → EDUKASI RINGAN
    # =========================
    else:
        if "program" in msg:
            text += "\n\nBiasanya anak jadi lebih cepat lancar baca 😊"

    data["reply"] = text
    return data


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
# MAIN AI FUNCTION
# =========================
def run_ai(user_id: str, message: str):

    # =========================
    # INIT MEMORY
    # =========================
    if user_id not in chat_memory:
        chat_memory[user_id] = []

    history = chat_memory[user_id]

    # ✅ FIX sapaan
    is_first_chat = len(history) == 0

    # =========================
    # GET USER DATA
    # =========================
    user = get_lead(user_id)

    nama = user.nama_orangtua if user and user.nama_orangtua else ""
    status_user = user.status if user and user.status else "COLD"

    # =========================
    # SAVE USER MESSAGE
    # =========================
    history.append({
        "role": "user",
        "content": message
    })

    chat_memory[user_id] = history[-MAX_HISTORY:]

    # =========================
    # SYSTEM CONTEXT
    # =========================
    system_context = SYSTEM_PROMPT + f"""

KONDISI: {'CHAT_PERTAMA' if is_first_chat else 'LANJUTAN'}
NAMA_USER: {nama}
STATUS_LEAD: {status_user}
"""

    # =========================
    # CALL AI
    # =========================
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_context},
            *chat_memory[user_id]
        ],
        max_output_tokens=300
    )

    ai_text = response.output_text
    print("AI RAW:", ai_text)

    data = safe_parse(ai_text)

    if not data.get("lead"):
        data["lead"] = {}

    # =========================
    # AUTO STATUS UPDATE
    # =========================
    msg = message.lower()

    if any(x in msg for x in ["daftar", "mau daftar", "join"]):
        data["status"] = "HOT"
    elif any(x in msg for x in ["tertarik", "info", "harga"]):
        data["status"] = "WARM"

    # =========================
    # FORMAT RESPONSE
    # =========================
    data = auto_closing(data, message, data.get("status", "COLD"))
    data["reply"] = format_reply(data["reply"])

    # =========================
    # SAVE TO DB
    # =========================
    save_lead(data, user_id)
    update_last_chat(user_id)

    # =========================
    # SAVE MEMORY
    # =========================
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

    if not lead:
        return

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