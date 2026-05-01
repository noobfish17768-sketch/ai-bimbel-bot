from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from database.models import LeadDB, Bot
from core.dependencies import get_db
from core.security import get_current_user_web, get_current_bot

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
def dashboard(
    request: Request,
    status: str = None,
    q: str = None,
    page: int = 1,
    db=Depends(get_db)
):

    user = get_current_user_web(request)

    if not hasattr(user, "id"):
        return user

    bot_id = get_current_bot(request, user)

    # fallback bot pertama (berdasarkan role)
    if not bot_id:

        if user.role == "owner":
            bot = db.query(Bot).filter(Bot.owner_id == user.id).first()
        else:
            bot = db.query(Bot).filter(Bot.user_id == user.id).first()

        if not bot:
            return {"error": "No bot found"}

        bot_id = bot.id

    per_page = 10

    base = db.query(LeadDB).filter(
        LeadDB.owner_id == user.id,
        LeadDB.bot_id == bot_id
    )

    hot = base.filter(LeadDB.status == "HOT").count()
    warm = base.filter(LeadDB.status == "WARM").count()
    cold = base.filter(LeadDB.status == "COLD").count()

    query = base

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

    total = query.count()

    # 🔥 FIX INI JUGA
    if user.role == "owner":
        bots = db.query(Bot).filter(Bot.owner_id == user.id).all()
    else:
        bots = db.query(Bot).filter(Bot.user_id == user.id).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "leads": leads,
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "total": total,
            "page": page,
            "bot_id": bot_id,
            "bots": bots,
            "current_bot_id": bot_id,
            "bot_active": getattr(user, "bot_active", True)
        }
    )