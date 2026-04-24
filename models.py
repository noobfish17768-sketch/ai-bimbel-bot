from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class LeadDB(Base):
    __tablename__ = "leads"

    # 🔥 FIX bentrok table (WAJIB di Railway / reload env)
    __table_args__ = {"extend_existing": True}

    # =========================
    # PRIMARY KEY
    # =========================
    id = Column(Integer, primary_key=True, index=True)

    # =========================
    # DATA USER
    # =========================
    nama_orangtua = Column(String, nullable=True)
    nama_anak = Column(String, nullable=True)
    umur_anak = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)

    # =========================
    # STATUS FUNNEL
    # =========================
    status = Column(String, default="COLD")

    # =========================
    # TIME TRACKING
    # =========================
    created_at = Column(DateTime, default=datetime.utcnow)
    last_chat = Column(DateTime, default=datetime.utcnow)

    # =========================
    # AI MEMORY (🔥 penting)
    # =========================
    chat_history = Column(String, nullable=True)

    # =========================
    # FOLLOW UP SYSTEM
    # =========================
    last_followup = Column(DateTime, nullable=True)
    next_followup = Column(DateTime, nullable=True)
    followup_count = Column(Integer, default=0)

    # =========================
    # AI SCORING
    # =========================
    lead_score = Column(Integer, default=0)

    # =========================
    # AI LEARNING SYSTEM
    # =========================
    converted = Column(Integer, default=0)      # 0 = belum daftar, 1 = sudah
    response_count = Column(Integer, default=0) # jumlah interaksi
