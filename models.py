from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class LeadDB(Base):
    __tablename__ = "leads"

    # 🔥 FIX duplicate load (Railway / reload / multi worker)
    __table_args__ = {"extend_existing": True}

    # =========================
    # PRIMARY KEY
    # =========================
    id = Column(Integer, primary_key=True, index=True)

    # =========================
    # USER DATA
    # =========================
    nama_orangtua = Column(String, nullable=True)
    nama_anak = Column(String, nullable=True)
    umur_anak = Column(String, nullable=True)

    # 🔥 penting → jangan nullable + harus unik
    whatsapp = Column(String, unique=True, index=True, nullable=False)

    # =========================
    # FUNNEL STATUS
    # =========================
    status = Column(String, default="COLD")

    # =========================
    # TIME TRACKING
    # =========================
    created_at = Column(DateTime, default=datetime.utcnow)
    last_chat = Column(DateTime, default=datetime.utcnow)

    # =========================
    # AI MEMORY (CHAT HISTORY)
    # =========================
    chat_history = Column(String, nullable=True)

    # =========================
    # FOLLOW-UP SYSTEM
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
    converted = Column(Integer, default=0)       # 0 = belum daftar, 1 = sudah
    response_count = Column(Integer, default=0)  # jumlah interaksi

    # =========================
    # DEBUG / MONITORING
    # =========================
    def __repr__(self):
        return f"<Lead {self.whatsapp} | {self.status} | score={self.lead_score}>"