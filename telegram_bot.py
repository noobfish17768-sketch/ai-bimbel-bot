from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from ai_service import run_ai
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    print("📩 MSG:", text)

    ai = run_ai(user_id, text)

    await update.message.reply_text("Bot aktif 24 jam 🚀")


def run_bot():
    print("🤖 BOT JALAN...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("BOT JALAN...")
    app.run_polling(drop_pending_updates=True)