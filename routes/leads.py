from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from database.models import LeadDB
from core.dependencies import get_db
from core.security import get_current_user_db

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadResponse(BaseModel):
    id: int
    nama_orangtua: Optional[str]
    nama_anak: Optional[str]
    whatsapp: str
    status: str

    class Config:
        from_attributes = True


@router.get("/")
def get_leads(request: Request, status: Optional[str] = None, q: Optional[str] = None, page: int = 1, db=Depends(get_db)):

    user_id = get_current_user_db(request)

    if not user_id:
        return {"error": "Unauthorized"}

    user_id = int(user_id)

    per_page = 10

    query = db.query(LeadDB).filter(LeadDB.owner_id == user_id)

    if status:
        query = query.filter(LeadDB.status == status)

    if q:
        query = query.filter(
            LeadDB.nama_orangtua.ilike(f"%{q}%") |
            LeadDB.whatsapp.ilike(f"%{q}%")
        )

    leads = query.order_by(LeadDB.created_at.desc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    return {
        "data": [LeadResponse.model_validate(l).model_dump() for l in leads],
        "total": query.count(),
        "page": page
    }


class UpdateStatusRequest(BaseModel):
    lead_id: int
    status: str


@router.post("/update-status")
def update_status(request: Request, data: UpdateStatusRequest, db=Depends(get_db)):

    user_id = get_current_user_db(request)

    if not user_id:
        return {"error": "Unauthorized"}

    if data.status not in ["HOT", "WARM", "COLD"]:
        return {"error": "Invalid status"}

    lead = db.query(LeadDB).filter(
        LeadDB.id == data.lead_id,
        LeadDB.owner_id == int(user_id)
    ).first()

    if not lead:
        return {"error": "Lead not found"}

    lead.status = data.status
    db.commit()

    return {"success": True}


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, request: Request, db=Depends(get_db)):

    user_id = get_current_user_db(request)

    if not user_id:
        return {"error": "Unauthorized"}

    lead = db.query(LeadDB).filter(
        LeadDB.id == lead_id,
        LeadDB.owner_id == int(user_id)
    ).first()

    if not lead:
        return {"error": "Not found"}

    db.delete(lead)
    db.commit()

    return {"success": True}