from database import engine, Base
import models # penting supaya model ke-load

def init_db():
    print("🚀 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database ready")

if __name__ == "__main__":
    init_db()