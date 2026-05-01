from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base


# =========================
# 👤 USER (OWNER SAAS)
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    created_at = Column(DateTime, server_default=func.now())

    # 🔗 RELATION
    bots = relationship("Bot", back_populates="owner", cascade="all, delete")


# =========================
# 🤖 BOT (MULTI BOT CORE)
# =========================
class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    user_id = Column(Integer, ForeignKey("users.id"))   # user admin yang kelola bot
    name = Column(String)

    telegram_token = Column(String)   # 🔥 beda tiap client
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())

    # 🔗 RELATION
    owner = relationship("User", back_populates="bots")
    leads = relationship("LeadDB", back_populates="bot", cascade="all, delete")
    settings = relationship("BotSetting", back_populates="bot", cascade="all, delete")


# =========================
# 📇 LEADS
# =========================
class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)

    telegram_id = Column(String, index=True)
    whatsapp = Column(String, index=True)

    nama_orangtua = Column(String)
    nama_anak = Column(String)
    umur_anak = Column(String)

    status = Column(String, default="COLD")
    notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    last_chat = Column(DateTime, server_default=func.now())

    followup_count = Column(Integer, default=0)
    lead_score = Column(Integer, default=0)

    # 🔗 RELATION
    bot = relationship("Bot", back_populates="leads")
    conversations = relationship("Conversation", back_populates="lead", cascade="all, delete-orphan")


# =========================
# 💬 CONVERSATION
# =========================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"))
    lead_id = Column(Integer, ForeignKey("leads.id"))

    message = Column(Text)
    response = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    lead = relationship("LeadDB", back_populates="conversations")


# =========================
# ⚙️ BOT SETTINGS
# =========================
class BotSetting(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"))

    key = Column(String)
    value = Column(String)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bot = relationship("Bot", back_populates="settings")