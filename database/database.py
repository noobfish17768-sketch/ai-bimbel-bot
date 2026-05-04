from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

print("🛢️ DATABASE CONNECTING...")

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL tidak ditemukan")

# =========================
# FIX POSTGRES URL (Railway)
# =========================
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# =========================
# SSL CONFIG (SMART)
# =========================
connect_args = {}

if "postgresql" in DATABASE_URL:
    if settings.ENV == "production":
        connect_args = {"sslmode": "require"}
    else:
        connect_args = {}

# =========================
# ENGINE
# =========================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,         # 🔥 naik dari 5
    max_overflow=20,      # 🔥 naik dari 10
    echo=settings.DEBUG,  # 🔥 log query kalau dev
    connect_args=connect_args
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

print(f"✅ DATABASE READY ({settings.ENV})")