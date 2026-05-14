import json
import os
import openai
import re
print("OPENAI FILE:", openai.__file__)
print("OPENAI VERSION:", openai.__version__)

from openai import OpenAI
from database.database import SessionLocal
from database.models import LeadDB, Conversation, Bot, BotKnowledge, BotFAQ
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MAX_HISTORY = 6


# =========================
# SAFE JSON PARSER
# =========================
def safe_parse(text):

    if not text:
        return {"reply": ""}

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)

    except Exception:

        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            cleaned = text[start:end]

            return json.loads(cleaned)

        except Exception:
            return {
                "reply": text,
                "lead": {}
            }


# =========================
# FORMAT
# =========================
def format_reply(text):
    if not text:
        return ""
    return "\n".join([l.strip() for l in text.split("\n")])


# =========================
# LOAD HISTORY
# =========================
def load_history(db, lead_id):
    chats = db.query(Conversation).filter(
        Conversation.lead_id == lead_id
    ).order_by(Conversation.id.desc()).limit(MAX_HISTORY).all()

    history = []
    for c in reversed(chats):
        if c.message:
            history.append({"role": "user", "content": c.message})
        if c.response:
            history.append({"role": "assistant", "content": c.response})

    return history


# =========================
# STATUS DETECTION
# =========================
def detect_status(message, current):
    msg = message.lower()

    if any(x in msg for x in ["daftar", "join", "ikut", "pesen", "order"]):
        return "HOT"
    if any(x in msg for x in ["harga", "jadwal", "info", "berapa", "menu"]):
        return "WARM"
    return current

STATUS_ORDER = {
    "COLD": 1,
    "WARM": 2,
    "HOT": 3,
    "CLOSING": 4
}

# =========================
# PAYMENT DETECT
# =========================
def detect_payment_confirmation(message):
    msg = message.lower()

    keywords = [
        "sudah transfer",
        "udah transfer",
        "bukti transfer",
        "sudah bayar",
        "udah bayar",
        "done transfer",
        "saya sudah transfer",
        "sudah tf"
    ]

    return any(x in msg for x in keywords)


# =========================
# FUNNEL
# =========================
def determine_stage(score):
    if score >= 80:
        return "HOT"
    elif score >= 50:
        return "WARM"
    else:
        return "COLD"


# =========================
# INTENT
# =========================
def detect_intent(message):
    msg = message.lower()

    if any(x in msg for x in ["daftar", "join", "order", "beli"]):
        return "buying"

    if any(x in msg for x in ["harga", "biaya", "jadwal"]):
        return "considering"

    return "exploring"


# =========================
# SCORE SYSTEM (FIXED)
# =========================
def calculate_score(message, status, prev, last_chat=None):
    msg = message.lower()
    score = prev or 0

    if last_chat:
        hours_passed = (datetime.utcnow() - last_chat).total_seconds() / 3600
        decay = int(hours_passed // 24) * 3
        score = max(score - decay, 0)

    score += 2

    if status == "WARM":
        score += 10
    elif status == "HOT":
        score += 20
    elif status == "CLOSING":
        score += 35

    if any(x in msg for x in ["daftar", "join", "order", "beli"]):
        score += 25

    if any(x in msg for x in ["saya mau", "langsung", "sekarang"]):
        score += 30

    if any(x in msg for x in ["harga", "jadwal", "info"]):
        score += 10

    return min(score, 100)


# =========================
# REQUIRED FIELDS (ONLY ONE VERSION)
# =========================
def get_required_fields(status, intent, lead):

    fields = []

    if status == "COLD":
        fields.append("nama_orangtua")

    elif status == "WARM":
        fields.extend(["nama_anak", "umur_anak"])

    elif status == "HOT":
        fields.extend(["nama_anak", "umur_anak", "whatsapp"])

    if intent == "buying":
        fields.append("whatsapp")

    if intent == "considering":
        fields.append("umur_anak")

    return list(set([f for f in fields if not getattr(lead, f)]))


# =========================
# LEAD EXTRACTION (FIXED SAFE ORDER)
# =========================
def extract_lead_data(message):
    raw = message.lower()
    normalized = re.sub(r'\D', '', raw)

    data = {}

    # WA FIRST (IMPORTANT)
    m = re.search(r'(08\d{8,13}|628\d{8,13})', normalized)
    if m:
        wa = m.group(1)
        if wa.startswith("08"):
            wa = "62" + wa[1:]
        if 10 <= len(wa) <= 15:
            data["whatsapp"] = wa

    # CLEAN TEXT AFTER WA REMOVED
    clean = re.sub(r'(08\d{8,13}|628\d{8,13})', '', raw)
    clean = re.sub(r'\b\d{1,2}\b', '', clean)

    # ORANG TUA
    m = re.search(r'\b(aku|saya|sy)\s+([a-zA-Z]{3,20}(?:\s[a-zA-Z]{3,20})?)\b', clean)
    if m:
        nama = m.group(2).split()[0]
        if not any(char.isdigit() for char in nama):
            if nama.lower() not in ["phone", "num"]:
                data["nama_orangtua"] = nama.title()

    # UMUR
    m = re.search(r'(\d+)\s*(tahun|th)', raw)
    if m:
        data["umur_anak"] = int(m.group(1))

    # NAMA ANAK
    m = re.search(r'(namanya|anakku|anak saya)\s+([a-zA-Z ]{2,30})', clean)
    if m:
        data["nama_anak"] = m.group(2).split()[0].title()

    return data

# =========================
# DETECT CLOSING INTENT
# =========================
def detect_closing(message):
    msg = message.lower()

    closing_keywords = [
        "mau daftar",
        "siap bayar",
        "transfer",
        "qris",
        "bayar sekarang",
        "gas daftar",
        "ambil slot",
        "lanjut pembayaran",
        "fix daftar",
        "saya transfer",
        "boleh kirim pembayaran",
        "ambil paket",
        "jadi daftar",
        "deal",
        "checkout",
        "lanjut bayar"
    ]

    return any(x in msg for x in closing_keywords)

# =========================
# MAIN ENGINE
# =========================
def run_ai(user_id: str, message: str, owner_id: int, bot_id: int, system_prompt: str):

    db = SessionLocal()

    try:
        user_id = str(user_id)

        lead = db.query(LeadDB).filter(
            LeadDB.telegram_id == user_id,
            LeadDB.bot_id == bot_id
        ).first()

        if not lead:
            lead = LeadDB(
                telegram_id=user_id,
                bot_id=bot_id,
                status="COLD",
                lead_score=0,
                last_chat=datetime.utcnow()
            )
            db.add(lead)
            db.flush()

        if hasattr(lead, "ai_enabled") and not lead.ai_enabled:
            return None

        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        current_status = lead.status
        if current_status == "CLOSING":
            new_status = "CLOSING"

        prev_score = lead.lead_score

        # =====================
        # EXTRACT
        # =====================
        lead_data = extract_lead_data(message)

        intent = detect_intent(message)

        is_closing = detect_closing(message)

        detected = detect_status(message, current_status)

        if STATUS_ORDER.get(detected, 0) >= STATUS_ORDER.get(current_status, 0):
            new_status = detected
        else:
            new_status = current_status

        missing_fields = []

        if is_closing:

            # saat closing cuma minta data kritikal
            critical_fields = ["whatsapp"]

            missing_fields = [
                f for f in critical_fields
                if not getattr(lead, f)
            ]

        else:
            missing_fields = get_required_fields(new_status, intent, lead)
        
        if detect_payment_confirmation(message):
            lead.payment_status = "WAITING_CONFIRMATION"

        # =====================
        # PAYMENT INFO
        # =====================
        payment_info = f"""
        METODE PEMBAYARAN:

        🏦 Transfer Bank:
        {getattr(bot, "bank_name", "-")} - {getattr(bot, "rekening", "-")}

        📱 QRIS:
        {getattr(bot, "qris_url", "-")}
        """

        if not getattr(bot, "rekening", None):
            payment_info = """
            Pembayaran akan dikirim admin secara manual.
            """

        invoice_id = f"INV-{lead.id}-{int(datetime.utcnow().timestamp())}"

        
        
        # =====================
        # HISTORY
        # =====================
        history = load_history(db, lead.id)
        history.append({"role": "user", "content": message})

        # =====================
        # MEMORY
        # =====================
        long_term_memory = ""
        if lead.last_summary:
            long_term_memory = f"""
LONG TERM MEMORY:
{lead.last_summary}
"""

        # =====================
        # KB
        # =====================
        knowledge_items = db.query(BotKnowledge).filter(BotKnowledge.bot_id == bot_id).all()
        faq_items = db.query(BotFAQ).filter(BotFAQ.bot_id == bot_id).all()

        knowledge_text = "\n".join([f"- {i.content}" for i in knowledge_items])
        faq_text = "\n".join([f"Q:{f.question} A:{f.answer}" for f in faq_items])

        # =====================
        # CLOSING MODE
        # =====================

        closing_prompt = ""

        if is_closing:

            new_status = "CLOSING"

            closing_prompt = f"""

        =====================
        CLOSING MODE ACTIVE
        =====================

        Gunakan informasi pembayaran ini:

        {payment_info}

        Instruksi:
        - Jangan lagi tanya data panjang
        - Fokus bantu closing
        - Jelaskan cara pembayaran dengan jelas
        - Jangan buat nomor rekening baru
        - Jangan improvisasi
        - Arahkan user untuk transfer / scan QRIS
        - Jika user siap bayar → arahkan langsung transfer
        - DILARANG membalas selain JSON
        - Jangan gunakan markdown
        - Jangan gunakan ```json
        - Output wajib valid JSON
        """
            
        new_score = calculate_score(message, new_status, prev_score, lead.last_chat)

        # =====================
        # SYSTEM PROMPT (FIX: ADD FOCUS)
        # =====================
        system_context = f"""
{system_prompt}

STATUS: {new_status}
INTENT: {intent}

MISSING_FIELDS_TO_COLLECT:
{missing_fields}

{long_term_memory}

KNOWLEDGE:
{knowledge_text}

FAQ:
{faq_text}

Invoice ID:
{invoice_id}

=====================
RULES 
===================== 
- Gunakan knowledge base 
- Jangan mengarang 
- Jika data tidak ada, bilang akan dicek admin 
- Jangan membuat harga sendiri 
- Jangan membuat jadwal sendiri 
- Jangan mengarang promo 
- Jawab berdasarkan knowledge base
- DILARANG membuat rekening sendiri
- DILARANG membuat QRIS sendiri
- Gunakan EXACT payment info dari sistem
- Jika payment info kosong → bilang admin akan mengirim pembayaran

Jika CLOSING_MODE = TRUE:
- Jangan lagi tanya data
- Fokus ke:
  1. konfirmasi minat
  2. jelaskan harga singkat
  3. tampilkan metode pembayaran
  4. arahkan ke pembayaran langsung

Gaya bicara harus seperti sales closing, bukan edukasi.

WAJIB BALAS FORMAT JSON:

{
  "reply": "...",
  "lead": {
     "nama_orangtua": "",
     "nama_anak": "",
     "umur_anak": "",
     "whatsapp": ""
  }
}

{closing_prompt}
"""
        

        # =====================
        # AI CALL
        # =====================
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": system_context}, *history],
            temperature=0.7,
            max_tokens=300
        )

        ai_text = response.choices[0].message.content
        data = safe_parse(ai_text)

        reply = format_reply(data.get("reply", ""))

        ai_lead = data.get("lead", {})

        if "reply" not in data:
            data = {
                "reply": ai_text,
                "lead": {}
            }        

        final_lead = {
            "nama_orangtua":
                lead_data.get("nama_orangtua")
                or ai_lead.get("nama_orangtua"),

            "nama_anak":
                lead_data.get("nama_anak")
                or ai_lead.get("nama_anak"),

            "umur_anak":
                lead_data.get("umur_anak")
                or ai_lead.get("umur_anak"),

            "whatsapp":
                lead_data.get("whatsapp")
                or ai_lead.get("whatsapp"),
        }

        for k, v in final_lead.items():
            if v and not getattr(lead, k):
                setattr(lead, k, v)

        lead.status = new_status
        lead.lead_score = new_score
        lead.last_chat = datetime.utcnow()

        # SUMMARY MEMORY (hemat token)
        if lead.message_count > 0 and lead.message_count % 6 == 0:

            summary = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{
                    "role": "system",
                    "content": f"""
                    Ringkas customer berikut.

                    User: {message}
                    AI: {reply}

                    Fokus:
                    - nama
                    - minat
                    - kebutuhan
                    - status
                    - progress closing

                    Max 50 kata.
                    """
                }],
                max_tokens=100
            )

            lead.last_summary = summary.choices[0].message.content

        db.add(Conversation(
            bot_id=bot_id,
            lead_id=lead.id,
            message=message,
            response=reply,
            raw_response=ai_text,
            created_at=datetime.utcnow()
        ))

        lead.message_count = (lead.message_count or 0) + 1

        db.commit()

        return {
            "reply": reply,
            "status": new_status,
            "lead_score": new_score,
            "missing_fields": missing_fields
        }

    except Exception as e:
        db.rollback()
        print("RUN_AI ERROR:", e)
        return {"reply": "Error 🙏"}

    finally:
        db.close()