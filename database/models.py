from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, UniqueConstraint, Index
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

    role = Column(String, default="admin")

    created_at = Column(DateTime, server_default=func.now())

    bots_as_owner = relationship(
        "Bot",
        foreign_keys="[Bot.owner_id]",
        back_populates="owner"
    )

    bots_as_admin = relationship(
        "Bot",
        foreign_keys="[Bot.user_id]",
        back_populates="admin"
    )


# =========================
# 🤖 BOT (1 BOT = 1 PERSONA)
# =========================
class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    name = Column(String)
    telegram_token = Column(String)  # 🔥 keep this name CONSISTENT everywhere

    persona_type = Column(String, default="bimbel")  # 🔥 tambah default
    system_prompt = Column(Text)

    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="bots_as_owner"
    )

    admin = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="bots_as_admin"
    )
    knowledge_items = relationship(
        "BotKnowledge",
        back_populates="bot",
        cascade="all, delete"
    )

    faq_items = relationship(
        "BotFAQ",
        back_populates="bot",
        cascade="all, delete"
    )

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
    umur_anak = Column(Integer)

    status = Column(String, default="COLD", index=True)
    notes = Column(Text)
    minat = Column(Text)
    intent = Column(Text)
    last_summary = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    last_chat = Column(DateTime, server_default=func.now())

    followup_count = Column(Integer, default=0)
    lead_score = Column(Integer, default=0)
    is_human_takeover = Column(Boolean, default=False)
    ai_enabled = Column(Boolean, default=True)

    # 🔥 prevent duplicate lead per bot
    __table_args__ = (
        UniqueConstraint('bot_id', 'telegram_id', name='unique_bot_telegram'),
        Index('idx_bot_lastchat', 'bot_id', 'last_chat')  # 🔥 NEW
    )

    bot = relationship("Bot", back_populates="leads")
    conversations = relationship("Conversation", back_populates="lead", cascade="all, delete-orphan")


# =========================
# 💬 CONVERSATION
# =========================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)

    message = Column(Text)
    response = Column(Text)
    raw_response = Column(Text)

    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 🔥 RELATION TAMBAHAN (penting)
    bot = relationship("Bot")
    lead = relationship("LeadDB", back_populates="conversations")

    Index('idx_conversation_lead', 'lead_id', 'created_at')


# =========================
# ⚙️ BOT SETTINGS
# =========================
class BotSetting(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)

    key = Column(String)
    value = Column(String)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bot = relationship("Bot", back_populates="settings")

# =========================
# ⚙️ BOT KNOWLEDGE
# =========================
class BotKnowledge(Base):
    __tablename__ = "bot_knowledge"

    bot = relationship("Bot", back_populates="knowledge_items")

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)

    category = Column(String, default="general", index=True)
    title = Column(String, nullable=True)
    content = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())

    is_deleted = Column(Boolean, default=False)

    
# =========================
# ⚙️ BOT FAQ
# =========================
class BotFAQ(Base):
    __tablename__ = "bot_faq"

    bot = relationship("Bot", back_populates="faq_items")

    id = Column(Integer, primary_key=True)

    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)

    question = Column(Text)
    answer = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            'bot_id',
            'question',
            name='unique_bot_question'
        ),
    )