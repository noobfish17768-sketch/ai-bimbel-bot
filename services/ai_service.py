import json
import os
import openai
print("OPENAI FILE:", openai.__file__)
print("OPENAI VERSION:", openai.__version__)
from openai import OpenAI
from database.database import SessionLocal
from database.models import LeadDB, Conversation, Bot
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MAX_HISTORY = 6


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
        # 💬 LOAD HISTORY
        # =========================
        history = load_history(db, lead.id)
        history.append({"role": "user", "content": message})

        # =========================
        # 🧠 SYSTEM PROMPT
        # =========================
        system_context = f"""
{system_prompt}

KONDISI: {'CHAT_PERTAMA' if len(history) <= 1 else 'LANJUTAN'}
STATUS_LEAD: {current_status}
"""

        # =========================
        # 🤖 AI CALL
        # =========================
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": system_context.strip()
                },
                *history
            ],
            temperature=0.7,
            max_output_tokens=300
        )

        ai_text = response.output_text
        data = safe_parse(ai_text)

        reply = format_reply(data.get("reply", ""))

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
        # 💾 SAVE CONVERSATION
        # =========================
        db.add(Conversation(
            bot_id=bot_id,
            lead_id=lead.id,
            message=message,
            response=reply,
            created_at=datetime.utcnow()
        ))

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