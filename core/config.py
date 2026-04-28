import os
from dotenv import load_dotenv

load_dotenv()


# =========================
# APP CONFIG
# =========================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")
DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# OPENAI
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# =========================
# TELEGRAM
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# =========================
# BOT CONFIG
# =========================
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 6))
BOT_FOLLOWUP_INTERVAL = int(os.getenv("BOT_FOLLOWUP_INTERVAL", 60))