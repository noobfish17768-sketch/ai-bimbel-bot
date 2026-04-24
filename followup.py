from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    nama_orangtua = Column(String, nullable=True)
    nama_anak = Column(String, nullable=True)
    umur_anak = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)

    status = Column(String, default="COLD")

    created_at = Column(DateTime, default=datetime.utcnow)
    last_chat = Column(DateTime, default=datetime.utcnow)
    chat_history = Column(String, nullable=True)

    # 🔥 WAJIB untuk followup system
    last_followup = Column(DateTime, nullable=True)
    lead_score = Column(Integer, default=0)
    next_followup = Column(DateTime, nullable=True)
    followup_count = Column(Integer, default=0)

    # 🔥 AI LEARNING
    converted = Column(Integer, default=0)  # 0 = belum, 1 = sudah daftar
    response_count = Column(Integer, default=0)