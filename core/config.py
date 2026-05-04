import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # =========================
    # ENVIRONMENT
    # =========================
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = ENV != "production"

    # =========================
    # APP
    # =========================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret")
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # =========================
    # OPENAI
    # =========================
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    # =========================
    # BOT CONFIG
    # =========================
    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", 6))
    BOT_FOLLOWUP_INTERVAL: int = int(os.getenv("BOT_FOLLOWUP_INTERVAL", 60))

    # =========================
    # REDIS
    # =========================
    REDIS_URL: str = os.getenv("REDIS_URL")

    # =========================
    # LOGGING
    # =========================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# =========================
# GLOBAL INSTANCE
# =========================
settings = Settings()