from services.ai_service import run_ai
from cache.cache import redis_client
from database.database import SessionLocal
from database.models import Bot, LeadDB
from services.ws_manager import manager


# =========================
# DEFAULT PROMPTS
# =========================
DEFAULT_PROMPTS = {
    "bimbel": """
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
""",

    "curhat": """
Kamu adalah Abang sebagai teman curhat yang empatik dan santai.

Gaya:
- berperilaku seperti Abang
- Hangat, santai, seperti teman
- Tidak menghakimi
- Tidak terlalu panjang

Aturan:
- Fokus dengarkan user
- Validasi perasaan
- Jangan kasih solusi terlalu cepat
- Jangan jualan apapun

Output JSON:
{
  "reply": "...",
  "lead": {},
  "status": "NEUTRAL"
}
""",

    "Jualan": """
Kamu adalah penjual roti bakar yang ramah dan persuasif.

Gaya:
- Santai, enak dibaca
- Seperti chat WhatsApp

Fokus:
- Jelaskan menu
- Rekomendasi produk
- Arahkan ke pembelian

Aturan:
- Jangan terlalu panjang
- Gunakan bahasa menggugah

Output JSON:
{
  "reply": "...",
  "lead": {},
  "status": "WARM"
}
"""
}


# =========================
# BOT ACTIVE CHECK
# =========================
def is_bot_active(bot_id: int) -> bool:

    if redis_client:
        try:
            cached = redis_client.get(f"bot:{bot_id}")
            if cached is not None:
                return cached.decode() == "True"
        except Exception as e:
            print("Redis error:", e)

    db = SessionLocal()
    try:
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        return bool(bot and bot.is_active)
    finally:
        db.close()


# =========================
# HANDLE MESSAGE
# =========================
async def handle_message(user_id: str, message: str, bot_id: int):

    if not message or not bot_id:
        return None

    # =========================
    # 🔥 BOT ACTIVE CHECK
    # =========================
    if not is_bot_active(bot_id):
        print(f"🤖 Bot OFF {bot_id}")
        return None

    db = SessionLocal()

    try:
        # =========================
        # 🔍 GET BOT
        # =========================
        bot = db.query(Bot).filter(Bot.id == bot_id).first()

        if not bot:
            return {"reply": "Bot tidak ditemukan"}

        # =========================
        # 🔍 GET LEAD
        # =========================
        lead = db.query(LeadDB).filter(
            LeadDB.whatsapp == str(user_id),
            LeadDB.bot_id == bot_id
        ).first()

        # =========================
        # 🧠 PROMPT
        # =========================
        system_prompt = bot.system_prompt or DEFAULT_PROMPTS.get(
            bot.persona_type,
            "Kamu adalah AI assistant yang ramah."
        )

        # =========================
        # 📡 PUSH USER MESSAGE (REALTIME)
        # =========================
        if lead:
            await manager.send_to_lead(lead.id, {
                "type": "message",
                "from": "user",
                "text": message
            })

        # =========================
        # 🛑 AI TAKEOVER CHECK
        # =========================
        if lead and hasattr(lead, "ai_enabled") and not lead.ai_enabled:
            print(f"🧑‍💻 Human takeover aktif (lead {lead.id})")
            return None

        # =========================
        # ✍️ TYPING START
        # =========================
        if lead:
            await manager.send_to_lead(lead.id, {
                "type": "typing",
                "from": "bot"
            })

        # =========================
        # 🤖 RUN AI
        # =========================
        result = run_ai(
            user_id=str(user_id),
            message=message,
            owner_id=bot.owner_id,
            bot_id=bot.id,
            system_prompt=system_prompt
        )

        if not result or not result.get("reply"):
            return None

        # =========================
        # ✍️ TYPING STOP
        # =========================
        if lead:
            await manager.send_to_lead(lead.id, {
                "type": "typing_stop",
                "from": "bot"
            })

        # =========================
        # 📡 PUSH BOT REPLY
        # =========================
        if lead:
            await manager.send_to_lead(lead.id, {
                "type": "message",
                "from": "bot",
                "text": result.get("reply")
            })

        return result

    except Exception as e:
        print("BOT ENGINE ERROR:", e)
        return {"reply": "System error 🙏"}

    finally:
        db.close()