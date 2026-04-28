from database.database import engine, Base
import database.models  # ensure models registered
import traceback


def init_db():
    try:
        print("🚀 Creating database tables...")

        Base.metadata.create_all(bind=engine)

        print("✅ Database ready successfully")

    except Exception as e:
        print("❌ Failed to create database")
        print(str(e))
        traceback.print_exc()


if __name__ == "__main__":
    init_db()