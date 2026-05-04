import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from database.models import BotSetting, Bot

db = SessionLocal()

def seed():
    # =========================
    # 🔍 AMBIL BOT PERTAMA
    # =========================
    bots = db.query(Bot).all()

    for bot in bots:
        for key, value in settings:
            exists = db.query(BotSetting).filter_by(
                bot_id=bot.id,
                key=key
            ).first()

            if not exists:
                db.add(BotSetting(
                    bot_id=bot.id,
                    key=key,
                    value=value
                ))

    if not bot:
        print("❌ Tidak ada bot, seed dibatalkan")
        return

    settings = [
        ("bot_status", "ON"),
        ("greeting", "Halo kak 😊"),
    ]

    for key, value in settings:
        exists = db.query(BotSetting).filter_by(
            bot_id=bot.id,
            key=key
        ).first()

        if not exists:
            db.add(BotSetting(
                bot_id=bot.id,
                key=key,
                value=value
            ))

    db.commit()
    print(f"✅ Seed done for bot_id={bot.id}")


if __name__ == "__main__":
    seed()