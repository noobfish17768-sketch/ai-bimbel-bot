from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from database.models import LeadDB, Bot
from core.dependencies import get_db
from core.security import get_current_user_db

router = APIRouter(prefix="/api/leads", tags=["leads"])


# =========================
# RESPONSE SCHEMA
# =========================
class LeadResponse(BaseModel):
    id: int
    nama_orangtua: Optional[str]
    nama_anak: Optional[str]
    whatsapp: str
    status: str

    class Config:
        from_attributes = True


# =========================
# GET LEADS (SECURE)
# =========================
@router.get("/")
def get_leads(
    request: Request,
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    db=Depends(get_db),
    user_id=Depends(get_current_user_db)
):

    bot_id = request.session.get("bot_id")

    if not bot_id:
        raise HTTPException(400, "Bot not selected")

    # 🔒 VALIDASI BOT OWNER
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user_id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    per_page = 10

    query = db.query(LeadDB).filter(
        LeadDB.bot_id == bot.id
    )

    if status:
        query = query.filter(LeadDB.status == status)

    if q:
        query = query.filter(
            LeadDB.nama_orangtua.ilike(f"%{q}%") |
            LeadDB.whatsapp.ilike(f"%{q}%")
        )

    total = query.count()

    leads = query.order_by(LeadDB.created_at.desc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    return {
        "data": [LeadResponse.model_validate(l).model_dump() for l in leads],
        "total": total,
        "page": page
    }


# =========================
# UPDATE STATUS
# =========================
class UpdateStatusRequest(BaseModel):
    lead_id: int
    status: str


@router.post("/update-status")
def update_status(
    request: Request,
    data: UpdateStatusRequest,
    db=Depends(get_db),
    user_id=Depends(get_current_user_db)
):

    bot_id = request.session.get("bot_id")

    if not bot_id:
        raise HTTPException(400, "Bot not selected")

    if data.status not in ["HOT", "WARM", "COLD"]:
        raise HTTPException(400, "Invalid status")

    # 🔒 VALIDASI BOT
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user_id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    lead = db.query(LeadDB).filter(
        LeadDB.id == data.lead_id,
        LeadDB.bot_id == bot.id
    ).first()

    if not lead:
        raise HTTPException(404, "Lead not found")

    lead.status = data.status
    db.commit()

    return {"success": True}


# =========================
# DELETE LEAD
# =========================
@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    request: Request,
    db=Depends(get_db),
    user_id=Depends(get_current_user_db)
):

    bot_id = request.session.get("bot_id")

    if not bot_id:
        raise HTTPException(400, "Bot not selected")

    # 🔒 VALIDASI BOT
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user_id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    lead = db.query(LeadDB).filter(
        LeadDB.id == lead_id,
        LeadDB.bot_id == bot.id
    ).first()

    if not lead:
        raise HTTPException(404, "Lead not found")

    db.delete(lead)
    db.commit()

    return {"success": True}