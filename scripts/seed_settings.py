import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from database.models import BotSetting, Bot


def seed():
    db = SessionLocal()

    try:
        # =========================
        # 🔍 AMBIL SEMUA BOT
        # =========================
        bots = db.query(Bot).all()

        if not bots:
            print("❌ Tidak ada bot, seed dibatalkan")
            return

        # =========================
        # ⚙️ DEFAULT SETTINGS
        # =========================
        settings = [
            ("bot_status", "ON"),
            ("greeting", "Halo kak 😊"),
        ]

        # =========================
        # 🔁 LOOP SEMUA BOT
        # =========================
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

            print(f"✅ Seeded bot_id={bot.id}")

        db.commit()

    except Exception as e:
        print("❌ SEED ERROR:", e)

    finally:
        db.close()


if __name__ == "__app__":
    seed()