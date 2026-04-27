from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


# =========================
# 👤 USER (ADMIN / SAAS USER)
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    role = Column(String, default="admin")  # superadmin / admin / staff

    created_at = Column(DateTime, server_default=func.now())

    # 🔗 RELATION
    leads = relationship(
        "LeadDB",
        back_populates="owner",
        foreign_keys="LeadDB.owner_id",
        cascade="all, delete"
    )

    assigned_leads = relationship(
        "LeadDB",
        foreign_keys="LeadDB.assigned_to"
    )

    def __repr__(self):
        return f"<User {self.username} | {self.role}>"


# =========================
# 📇 LEADS (MULTI TENANT + CRM)
# =========================
class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)

    # 🔥 MULTI TENANT (WAJIB)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 🔥 ASSIGN KE STAFF
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    telegram_id = Column(String, unique=True, index=True)

    nama_orangtua = Column(String)
    nama_anak = Column(String)
    umur_anak = Column(String)

    whatsapp = Column(String, unique=True, index=True, nullable=False)

    status = Column(String, default="COLD")

    # 🧠 CRM
    notes = Column(Text)

    # 📊 TRACKING
    created_at = Column(DateTime, server_default=func.now())
    last_chat = Column(DateTime, server_default=func.now())

    chat_history = Column(Text)

    last_followup = Column(DateTime)
    next_followup = Column(DateTime)

    followup_count = Column(Integer, default=0)

    lead_score = Column(Integer, default=0)

    converted = Column(Integer, default=0)
    response_count = Column(Integer, default=0)

    # 🔗 RELATION
    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="leads"
    )

    conversations = relationship(
        "Conversation",
        back_populates="lead",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Lead {self.whatsapp} | {self.status}>"


# =========================
# 💬 CONVERSATIONS
# =========================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)

    user_id = Column(String, index=True)  # telegram user id

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    message = Column(Text)
    response = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    # 🔗 RELATION
    lead = relationship("LeadDB", back_populates="conversations")

    def __repr__(self):
        return f"<Chat {self.user_id}>"


# =========================
# ⚙️ BOT SETTINGS
# =========================
class BotSetting(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)  # telegram user id
    key = Column(String, unique=True)
    value = Column(String)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"