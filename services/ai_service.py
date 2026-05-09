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

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}") + 1
        try:
            return json.loads(text[start:end])
        except:
            return {"reply": text}


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
    if any(x in msg for x in ["daftar", "mau", "join", "order"]):
        score += 20

    return min(score, 100)

# =========================
# LEAD EXTRACTION
# =========================
def extract_lead_data(message):
    text = message.lower()

    data = {}

    # nama orang tua
    m = re.search(
        r'(aku|saya|sy)\s+([a-zA-Z ]{2,30})',
        text
    )

    if m:
        nama = m.group(2).strip().split()[0]
        data["nama_orangtua"] = nama.title()

    # umur anak
    m = re.search(
        r'(\d+)\s*(tahun|th)',
        text
    )

    if m:
        data["umur_anak"] = int(m.group(1))

    # nama anak
    m = re.search(
        r'(namanya|anakku|anak saya)\s+([a-zA-Z ]{2,30})',
        text
    )

    if m:
        nama_anak = m.group(2).strip().split()[0]
        data["nama_anak"] = nama_anak.title()

    # nomer wa
    m = re.search(r'(08\d{8,13}|628\d{7,13})', text)
    if m:
        whatsapp = m.group(1)

        # convert 08 -> 628
        if whatsapp.startswith("08"):
            whatsapp = "62" + whatsapp[1:]

        # validasi panjang nomer
        if 10 <= len(whatsapp) <= 15:
            data["whatsapp"] = whatsapp

    return data


# =========================
# MAIN AI
# =========================
def run_ai(user_id: str, message: str, owner_id: int, bot_id: int, system_prompt: str):

    db = SessionLocal()
    
    try:
        user_id = str(user_id)

        # =========================
        # 🔍 GET / CREATE LEAD
        # =========================
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
        
        # =========================
        # 🛑 HUMAN TAKEOVER CHECK
        # =========================
        if hasattr(lead, "ai_enabled") and not lead.ai_enabled:
            print(f"⛔ AI SKIPPED (lead {lead.id})")
            return None

        # =========================
        # 🤖 GET BOT (FIX BUG)
        # =========================
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        current_status = lead.status
        prev_score = lead.lead_score

        # =========================
        # 🧠 EXTRACT LEAD DATA
        # =========================
        lead_data = extract_lead_data(message)

        print("EXTRACTED:", lead_data)

        # =========================
        # 🧠 LONG TERM MEMORY
        # =========================
        long_term_memory = ""

        if lead.last_summary:
            long_term_memory = f"""
            =====================
            LONG TERM MEMORY
            =====================

            {lead.last_summary}
            """

        # =========================
        # 💬 LOAD HISTORY
        # =========================
        history = load_history(db, lead.id)
        history.append({"role": "user", "content": message})

        # =========================
        # 🧠 SYSTEM PROMPT
        # =========================
        knowledge_items = db.query(BotKnowledge).filter(
            BotKnowledge.bot_id == bot_id
        ).all()

        faq_items = db.query(BotFAQ).filter(
            BotFAQ.bot_id == bot_id
        ).all()

        knowledge_map = {}

        for item in knowledge_items:
            cat = item.category or "general"

            if cat not in knowledge_map:
                knowledge_map[cat] = []

            knowledge_map[cat].append(item)

        knowledge_text = ""

        for category, items in knowledge_map.items():

            knowledge_text += f"\n[{category.upper()}]\n"

            for item in items:

                if item.title:
                    knowledge_text += f"- {item.title}: {item.content}\n"
                else:
                    knowledge_text += f"- {item.content}\n"

        faq_text = "\n".join([
            f"Q: {f.question}\nA: {f.answer}"
            for f in faq_items
        ])

        if not knowledge_text:
            knowledge_text = "Belum ada knowledge base"

        if not faq_text:
            faq_text = "Belum ada FAQ"

        system_context = f"""
        {system_prompt}

        =====================
        KNOWLEDGE BASE
        =====================

        {knowledge_text}

        =====================
        FAQ
        =====================

        {faq_text}

        =====================
        LEAD MEMORY
        =====================

        {long_term_memory or "Belum ada summary"}
        
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

        KONDISI: {'CHAT_PERTAMA' if len(history) <= 1 else 'LANJUTAN'}
        STATUS_LEAD: {current_status}
        """
        
        # =========================
        # 🤖 AI CALL
        # =========================
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_context.strip()},
                *history
            ],
            temperature=0.7,
            max_tokens=300
        )

        ai_text = response.choices[0].message.content
        data = safe_parse(ai_text)
        ai_lead = data.get("lead", {})

        reply = format_reply(data.get("reply", ""))

        # =========================
        # MERGE LEAD DATA
        # PRIORITAS: AI > REGEX
        # =========================

        final_lead = {
            "nama_orangtua":
                ai_lead.get("nama_orangtua")
                or lead_data.get("nama_orangtua"),

            "nama_anak":
                ai_lead.get("nama_anak")
                or lead_data.get("nama_anak"),

            "umur_anak":
                ai_lead.get("umur_anak")
                or lead_data.get("umur_anak"),

            "whatsapp":
                ai_lead.get("whatsapp")
                or lead_data.get("whatsapp")
        }

        if final_lead.get("nama_orangtua") and not lead.nama_orangtua:
            lead.nama_orangtua = final_lead["nama_orangtua"]

        if final_lead.get("nama_anak") and not lead.nama_anak:
            lead.nama_anak = final_lead["nama_anak"]

        if final_lead.get("umur_anak") and not lead.umur_anak:
            lead.umur_anak = final_lead["umur_anak"]

        if final_lead.get("whatsapp") and not lead.whatsapp:
            lead.whatsapp = final_lead["whatsapp"]

        # =========================
        # 📊 STATUS & SCORING
        # =========================
        if bot and bot.persona_type != "curhat":
            new_status = detect_status(message, current_status)
            new_score = calculate_score(message, new_status, prev_score)

            lead.status = new_status
            lead.lead_score = new_score
        else:
            new_status = current_status
            new_score = prev_score

        lead.last_chat = datetime.utcnow()

        # =========================
        # SUMMARY AUTO
        # =========================
        summary_prompt = f"""
        Buat ringkasan singkat customer berikut.

        Isi:
        - nama
        - kebutuhan
        - minat
        - kendala
        - status

        Chat terakhir:
        User: {message}
        AI: {reply}

        Max 50 kata.
        """

        summary_response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": summary_prompt}
            ],
            max_tokens=100
        )

        lead.last_summary = summary_response.choices[0].message.content

        # =========================
        # 💾 SAVE CONVERSATION
        # =========================
        db.add(Conversation(
            bot_id=bot_id,
            lead_id=lead.id,
            message=message,
            response=reply,
            raw_response=ai_text,
            created_at=datetime.utcnow()
        ))
        print(
            "BEFORE SAVE:",
            lead.nama_orangtua,
            lead.nama_anak,
            lead.umur_anak
        )
        db.commit()

        return {
            "reply": reply,
            "status": new_status,
            "lead_score": new_score
        }

    except Exception as e:
        db.rollback()
        print("RUN_AI ERROR:", e)
        return {"reply": "Error 🙏"}

    finally:
        db.close()