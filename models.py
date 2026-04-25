from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)

    nama_orangtua = Column(String)
    nama_anak = Column(String)
    umur_anak = Column(String)

    whatsapp = Column(String, unique=True, index=True, nullable=False)

    status = Column(String, default="COLD")

    created_at = Column(DateTime, server_default=func.now())
    last_chat = Column(DateTime, server_default=func.now())

    chat_history = Column(Text)

    last_followup = Column(DateTime)
    next_followup = Column(DateTime)

    followup_count = Column(Integer, default=0)

    lead_score = Column(Integer, default=0)

    converted = Column(Integer, default=0)
    response_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Lead {self.whatsapp} | {self.status}>"