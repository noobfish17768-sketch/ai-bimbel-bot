from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
load_dotenv()

# =========================
# AMBIL DATABASE URL
# =========================
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./leads.db"
print("🛢️ DATABASE RAW:", repr(DATABASE_URL))
print("🛢️ DATABASE:", DATABASE_URL)

# =========================
# ENGINE SETUP
# =========================
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

# =========================
# SESSION
# =========================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =========================
# BASE MODEL
# =========================
Base = declarative_base()