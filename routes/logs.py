from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates

from database.models import Conversation, Bot
from core.dependencies import get_db
from core.security import get_current_user_web

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/conversations")
def conversations(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request)

    if not hasattr(user, "id"):
        return user

    bot_id = request.query_params.get("bot_id")
    lead_id = request.query_params.get("lead_id")
    q = request.query_params.get("q")

    # =========================
    # 🔒 VALIDASI BOT
    # =========================
    bot_ids = []

    if bot_id:
        try:
            bot_id = int(bot_id)
        except:
            raise HTTPException(400, "bot_id invalid")

        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.owner_id == user.id
        ).first()

        if not bot:
            raise HTTPException(403, "Akses ditolak")

        bot_ids = [bot.id]

    else:
        bots = db.query(Bot).filter(
            Bot.owner_id == user.id
        ).all()

        bot_ids = [b.id for b in bots]

    # =========================
    # 🔍 BASE QUERY
    # =========================
    query = db.query(Conversation).filter(
        Conversation.bot_id.in_(bot_ids)
    )

    # filter lead
    if lead_id:
        try:
            lead_id = int(lead_id)
        except:
            raise HTTPException(400, "lead_id invalid")

        query = query.filter(Conversation.lead_id == lead_id)

    # search text
    if q:
        query = query.filter(
            Conversation.message.ilike(f"%{q}%") |
            Conversation.response.ilike(f"%{q}%")
        )

    chats = query.order_by(Conversation.id.desc())\
        .limit(200)\
        .all()

    return templates.TemplateResponse(
        "conversations.html",
        {
            "request": request,
            "chats": chats,
            "selected_bot_id": bot_id,
            "selected_lead_id": lead_id,
            "query": q
        }
    )