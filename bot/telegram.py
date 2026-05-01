import os
from dotenv import load_dotenv
from telegram import Bot
from database.database import SessionLocal
from database.models import Bot as BotModel

load_dotenv()

# cache bot instance biar gak create ulang terus
BOT_CACHE = {}


def get_bot(bot_id: int):
    if bot_id in BOT_CACHE:
        return BOT_CACHE[bot_id]

    db = SessionLocal()
    try:
        bot_data = db.query(BotModel).filter(BotModel.id == bot_id).first()

        if not bot_data or not bot_data.token:
            print(f"❌ Bot {bot_id} token not found")
            return None

        bot = Bot(token=bot_data.token)

        BOT_CACHE[bot_id] = bot
        print(f"✅ Bot {bot_id} initialized")

        return bot

    finally:
        db.close()


# =========================
# SEND MESSAGE (MULTI BOT)
# =========================
async def send_telegram(bot_id: int, chat_id: str, text: str):

    bot = get_bot(bot_id)

    if not bot:
        return {"error": "bot not found"}

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return {"success": True}
    except Exception as e:
        print("❌ TELEGRAM ERROR:", e)
        return {"error": str(e)}