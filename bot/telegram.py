import os
from dotenv import load_dotenv
from telegram import Bot
from database.database import SessionLocal
from database.models import Bot as BotModel

load_dotenv()

# cache bot instance
BOT_CACHE = {}


def get_bot(bot_id: int):
    # =========================
    # CACHE HIT
    # =========================
    if bot_id in BOT_CACHE:
        return BOT_CACHE[bot_id]

    db = SessionLocal()

    try:
        bot_data = db.query(BotModel).filter(BotModel.id == bot_id).first()

        if not bot_data:
            print(f"❌ Bot {bot_id} tidak ditemukan")
            return None

        if not bot_data.telegram_token:
            print(f"❌ Bot {bot_id} tidak punya token")
            return None

        bot = Bot(token=bot_data.telegram_token)

        BOT_CACHE[bot_id] = bot

        print(f"✅ Bot {bot_id} initialized")

        return bot

    except Exception as e:
        print(f"❌ GET BOT ERROR {bot_id}:", e)
        return None

    finally:
        db.close()


# =========================
# OPTIONAL: CLEAR CACHE (kalau update token)
# =========================
def clear_bot_cache(bot_id: int):
    if bot_id in BOT_CACHE:
        del BOT_CACHE[bot_id]
        print(f"♻️ Cache cleared for bot {bot_id}")


# =========================
# SEND MESSAGE
# =========================
async def send_telegram(bot_id: int, chat_id: str, text: str):

    bot = get_bot(bot_id)

    if not bot:
        return {"error": "bot not found"}

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text
        )

        return {"success": True}

    except Exception as e:
        print(f"❌ TELEGRAM ERROR (bot {bot_id}):", e)

        # fallback: reset cache (biar reload token next request)
        clear_bot_cache(bot_id)

        return {"error": str(e)}