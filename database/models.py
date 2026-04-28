from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base


# =========================
# 👤 USER
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    role = Column(String, default="admin")

    # 🔥 SINGLE SOURCE OF TRUTH
    bot_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())

    # relasi ke leads
    leads = relationship(
        "LeadDB",
        back_populates="owner",
        foreign_keys="LeadDB.owner_id",
        cascade="all, delete"
    )

    # relasi assigned leads (optional future CRM)
    assigned_leads = relationship(
        "LeadDB",
        foreign_keys="LeadDB.assigned_to"
    )


# =========================
# 📇 LEADS
# =========================
class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    telegram_id = Column(String, unique=True, index=True)

    nama_orangtua = Column(String)
    nama_anak = Column(String)
    umur_anak = Column(String)

    whatsapp = Column(String, unique=True, index=True, nullable=False)

    status = Column(String, default="COLD")

    notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    last_chat = Column(DateTime, server_default=func.now())

    chat_history = Column(Text)

    last_followup = Column(DateTime)
    next_followup = Column(DateTime)

    followup_count = Column(Integer, default=0)
    lead_score = Column(Integer, default=0)

    converted = Column(Integer, default=0)
    response_count = Column(Integer, default=0)

    # relasi owner
    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="leads"
    )

    # relasi chat
    conversations = relationship(
        "Conversation",
        back_populates="lead",
        cascade="all, delete-orphan"
    )


# =========================
# 💬 CONVERSATIONS
# =========================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)

    user_id = Column(String, index=True)      # owner dashboard
    external_id = Column(String, index=True)  # telegram user

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    message = Column(Text)
    response = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    lead = relationship("LeadDB", back_populates="conversations")


# =========================
# ⚙️ BOT SETTINGS (CONFIG ONLY)
# =========================
class BotSetting(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True)

    user_id = Column(String, index=True)

    # 🔥 hanya config, bukan status bot
    key = Column(String, index=True)
    value = Column(String)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())