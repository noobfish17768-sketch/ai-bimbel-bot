from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, case

from database.models import LeadDB, Bot
from core.dependencies import get_db
from core.security import get_current_user_web

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# =========================
# BOT SELECTOR PAGE
# =========================
@router.get("/dashboard")
def dashboard_home(
    request: Request,
    db=Depends(get_db)
):
    user = get_current_user_web(request, db)

    if not hasattr(user, "id"):
        return user

    bots = db.query(
        Bot,
        func.count(LeadDB.id).label("total_leads"),
        func.sum(case((LeadDB.status == "HOT", 1), else_=0)).label("hot_leads"),
        func.coalesce(func.sum(LeadDB.revenue), 0).label("revenue")
    ).outerjoin(
        LeadDB, LeadDB.bot_id == Bot.id
    ).filter(
        (Bot.owner_id == user.id) |
        (Bot.user_id == user.id)
    ).group_by(Bot.id).all()

    bot_list = []

    for bot, total_leads, hot_leads, revenue in bots:
        bot_list.append({
            "id": bot.id,
            "name": bot.name,
            "persona_type": bot.persona_type,
            "is_active": bot.is_active,
            "total_leads": total_leads or 0,
            "hot_leads": hot_leads or 0,
            "revenue": revenue or 0,
        })

    # =========================
    # ADD THIS COUNT BLOCK HERE
    # =========================
    stats = db.query(
        LeadDB.status,
        func.count().label("count")
    ).join(Bot, Bot.id == LeadDB.bot_id).filter(
        (Bot.owner_id == user.id) |
        (Bot.user_id == user.id)
    ).group_by(LeadDB.status).all()

    counts = {s.status: s.count for s in stats}

    hot = counts.get("HOT", 0)
    warm = counts.get("WARM", 0)
    cold = counts.get("COLD", 0)
    total = sum(counts.values())

    # =========================
    # RETURN TEMPLATE
    # =========================
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "bots": bot_list,   # ← INI YANG DIPAKAI
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "total": total
        }
    )


# =========================
# SINGLE BOT DASHBOARD
# =========================
@router.get("/dashboard/{bot_id}")
def bot_dashboard(
    bot_id: int,
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
    # GET BOT
    # =========================
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        (
            (Bot.owner_id == user.id) |
            (Bot.user_id == user.id)
        )
    ).first()

    if not bot:
        return RedirectResponse("/dashboard")

    # =========================
    # STATS
    # =========================
    base = db.query(LeadDB).filter(
        LeadDB.bot_id == bot_id
    )

    stats = db.query(
        LeadDB.status,
        func.count().label("count")
    ).filter(
        LeadDB.bot_id == bot_id
    ).group_by(LeadDB.status).all()

    counts = {s.status: s.count for s in stats}

    hot = counts.get("HOT", 0)
    warm = counts.get("WARM", 0)
    cold = counts.get("COLD", 0)

    query = base

    if status:
        query = query.filter(
            LeadDB.status == status
        )

    if q:
        query = query.filter(
            LeadDB.nama_orangtua.ilike(f"%{q}%") |
            LeadDB.whatsapp.ilike(f"%{q}%")
        )

    per_page = 10

    leads = query.order_by(
        LeadDB.created_at.desc()
    ).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    total = query.count()

    return templates.TemplateResponse(
        "bot_dashboard.html",
        {
            "request": request,
            "bot": bot,
            "bot_id": bot.id,
            "leads": leads,
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "total": total,
            "page": page,
            "q" : q
        }
    )