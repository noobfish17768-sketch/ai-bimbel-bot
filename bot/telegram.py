import os
from dotenv import load_dotenv
from telegram import Bot

# load env
load_dotenv()

# =========================
# CONFIG
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# =========================
# INIT BOT (sekali saja)
# =========================
if TELEGRAM_TOKEN:
    bot = Bot(token=TELEGRAM_TOKEN)
    print("✅ Bot Telegram Ready")
else:
    bot = None
    print("❌ TELEGRAM TOKEN NOT FOUND")


# =========================
# SEND MESSAGE (REUSABLE)
# =========================
async def send_telegram(chat_id: str, text: str):
    if not bot:
        return {"error": "bot not ready"}

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return {"success": True}
    except Exception as e:
        print("❌ TELEGRAM ERROR:", e)
        return {"error": str(e)}