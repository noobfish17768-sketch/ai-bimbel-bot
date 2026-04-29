from database.database import SessionLocal
from database.models import BotSetting

db = SessionLocal()

def seed():
    settings = [
        ("bot_status", "ON"),
        ("greeting", "Halo kak 😊"),
    ]

    for key, value in settings:
        exists = db.query(BotSetting).filter_by(
            user_id="1",
            key=key
        ).first()

        if not exists:
            db.add(BotSetting(
                user_id="1",
                key=key,
                value=value
            ))

    db.commit()
    print("✅ Seed done")

if __name__ == "__main__":
    seed()