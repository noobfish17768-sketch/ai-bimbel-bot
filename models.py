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
    last_chat = Column(DateTime, nullable=True)