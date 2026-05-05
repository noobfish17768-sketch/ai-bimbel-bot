from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database.models import LeadDB, Conversation, Bot
from core.dependencies import get_db
from core.security import get_current_user_web
from bot.telegram import send_telegram
from services.ws_manager import manager

from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# =========================
# 📥 INBOX VIEW
# =========================
@router.get("/inbox")
def inbox(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request,db)

    if not hasattr(user, "id"):
        return user

    bot_id = request.query_params.get("bot_id")
    lead_id = request.query_params.get("lead_id")

    leads = []
    chats = []
    active_lead = None

    # =========================
    # 🔒 VALIDASI BOT
    # =========================
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

        leads = db.query(LeadDB)\
            .filter(LeadDB.bot_id == bot.id)\
            .order_by(LeadDB.last_chat.desc())\
            .limit(100)\
            .all()

    else:
        bots = db.query(Bot).filter(
            Bot.owner_id == user.id
        ).all()

        bot_ids = [b.id for b in bots]

        if bot_ids:
            leads = db.query(LeadDB)\
                .filter(LeadDB.bot_id.in_(bot_ids))\
                .order_by(LeadDB.last_chat.desc())\
                .limit(100)\
                .all()

    # =========================
    # 💬 CHAT AKTIF
    # =========================
    if lead_id:
        try:
            lead_id = int(lead_id)
        except:
            raise HTTPException(400, "lead_id invalid")

        active_lead = db.query(LeadDB).join(Bot).filter(
            LeadDB.id == lead_id,
            Bot.owner_id == user.id
        ).first()

        if not active_lead:
            raise HTTPException(403, "Lead tidak valid")

        chats = db.query(Conversation)\
            .filter(Conversation.lead_id == lead_id)\
            .order_by(Conversation.id.asc())\
            .all()

    return templates.TemplateResponse(
        "inbox.html",
        {
            "request": request,
            "leads": leads,
            "chats": chats,
            "active_lead": active_lead,
            "bot_id": bot_id
        }
    )


# =========================
# 📤 MANUAL REPLY (AUTO PAUSE + REALTIME)
# =========================
@router.post("/api/inbox/reply")
async def manual_reply(
    request: Request,
    db=Depends(get_db),
):
    user = get_current_user_web(request, db)

    if not hasattr(user, "id"):
        raise HTTPException(401)

    form = await request.form()

    lead_id = form.get("lead_id")
    message = form.get("message")

    if not lead_id:
        raise HTTPException(400, "lead_id wajib")

    try:
        lead_id = int(lead_id)
    except:
        raise HTTPException(400, "lead_id invalid")

    if not message or not message.strip():
        raise HTTPException(400, "Pesan kosong")

    message = message.strip()

    # =========================
    # 🔍 GET LEAD
    # =========================
    lead = db.query(LeadDB).filter(
        LeadDB.id == lead_id
    ).first()

    if not lead:
        raise HTTPException(404, "Lead tidak ditemukan")

    # =========================
    # 🔒 VALIDASI BOT
    # =========================
    bot = db.query(Bot).filter(
        Bot.id == lead.bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    # =========================
    # 🛑 AUTO PAUSE AI
    # =========================
    if getattr(lead, "ai_enabled", True):
        print(f"🛑 AI AUTO-PAUSED (lead {lead.id})")
        lead.ai_enabled = False

    # =========================
    # 📤 SEND TELEGRAM
    # =========================
    if not lead.telegram_id:
        raise HTTPException(400, "Telegram ID tidak tersedia")

    result = await send_telegram(
        bot_id=bot.id,
        chat_id=lead.telegram_id,
        text=message
    )

    if "error" in result:
        raise HTTPException(500, result["error"])

    # =========================
    # 📡 REALTIME PUSH
    # =========================
    await manager.send_to_lead(lead.id, {
        "type": "message",
        "from": "admin",
        "text": message
    })

    # =========================
    # 💾 SAVE CHAT
    # =========================
    db.add(Conversation(
        bot_id=bot.id,
        lead_id=lead.id,
        message="[MANUAL]",
        response=message,
        created_at=datetime.utcnow()
    ))

    lead.last_chat = datetime.utcnow()

    db.commit()

    return RedirectResponse(
        f"/inbox?bot_id={bot.id}&lead_id={lead.id}",
        status_code=303
    )


# =========================
# 🔁 TOGGLE AI
# =========================
@router.post("/api/inbox/toggle-ai")
async def toggle_ai(
    request: Request,
    db=Depends(get_db),
):
    user = get_current_user_web(request, db)

    if not hasattr(user, "id"):
        raise HTTPException(401)

    form = await request.form()
    lead_id = form.get("lead_id")

    if not lead_id:
        raise HTTPException(400, "lead_id wajib")

    try:
        lead_id = int(lead_id)
    except:
        raise HTTPException(400, "lead_id invalid")

    lead = db.query(LeadDB).join(Bot).filter(
        LeadDB.id == lead_id,
        Bot.owner_id == user.id
    ).first()

    if not lead:
        raise HTTPException(404, "Lead not found")

    lead.ai_enabled = not lead.ai_enabled
    db.commit()

    print(f"🔁 AI TOGGLED lead {lead.id} -> {lead.ai_enabled}")

    return RedirectResponse(
        f"/inbox?bot_id={lead.bot_id}&lead_id={lead.id}",
        status_code=303
    )