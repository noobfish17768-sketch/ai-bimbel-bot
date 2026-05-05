from fastapi import APIRouter, Request, Depends, HTTPException
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
    user = get_current_user_web(request, db)

    if not hasattr(user, "id"):
        return user

    # =========================
    # 🔍 GET BOT (SAFE)
    # =========================
    bot = get_current_bot(request, user, db)

    if not bot:
        # fallback ambil bot pertama milik user
        bot = db.query(Bot).filter(
            (Bot.owner_id == user.id) | (Bot.user_id == user.id)
        ).first()

        if not bot:
            return RedirectResponse("/create-bot", status_code=302)

    bot_id = bot.id

    # =========================
    # 📊 BASE QUERY
    # =========================
    base = db.query(LeadDB).filter(LeadDB.bot_id == bot_id)

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

    per_page = 10

    leads = query.order_by(LeadDB.created_at.desc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    total = query.count()

    # =========================
    # 🤖 BOT LIST (CONSISTENT)
    # =========================
    bots = db.query(Bot).filter(
        (Bot.owner_id == user.id) | (Bot.user_id == user.id)
    ).all()

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
            "current_bot": bot,
            "current_bot_id": bot_id,
            "bot_active": bot.is_active
        }
    )