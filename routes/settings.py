from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database.models import BotSetting, Bot, BotKnowledge, BotFAQ
from core.dependencies import get_db
from core.security import get_current_user_web, get_current_user_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# =========================
# GET SETTINGS
# =========================
@router.get("/settings")
def settings_page(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request,db)

    if not hasattr(user, "id"):
        return user

    bot_id = request.query_params.get("bot_id")

    if not bot_id:
        return RedirectResponse("/dashboard", status_code=302)

    try:
        bot_id = int(bot_id)
    except:
        return RedirectResponse("/dashboard", status_code=302)

    # 🔒 VALIDASI BOT
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        return RedirectResponse("/dashboard", status_code=302)

    settings = db.query(BotSetting).filter(
        BotSetting.bot_id == bot.id
    ).all()

    knowledge_items = sorted(
        bot.knowledge_items,
        key=lambda x: x.id,
        reverse=True
    )

    faq_items = sorted(
        bot.faq_items,
        key=lambda x: x.id,
        reverse=True
    )
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "bot_id": bot.id,
            "knowledge_items": knowledge_items,
            "faq_items": faq_items
        }
    )


# 🔥 UPGRADE: support casting
def get_setting(db, bot_id: int, key: str, default=None, cast=str):
    s = db.query(BotSetting).filter(
        BotSetting.bot_id == bot_id,
        BotSetting.key == key
    ).first()

    if not s:
        return default

    try:
        return cast(s.value)
    except:
        return default


class SettingUpdate(BaseModel):
    bot_id: int
    key: str
    value: str

# =========================
# CREATE SETTINGS
# =========================
@router.post("/api/settings")
async def update_setting(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    # 🔥 SAFE PARSE
    bot_id_raw = form.get("bot_id")
    key = form.get("key")
    value = form.get("value")

    if not bot_id_raw or not key:
        raise HTTPException(400, "bot_id & key wajib")

    try:
        bot_id = int(bot_id_raw)
    except:
        raise HTTPException(400, "bot_id invalid")

    # 🔒 VALIDASI BOT
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    setting = db.query(BotSetting).filter(
        BotSetting.bot_id == bot.id,
        BotSetting.key == key
    ).first()

    if setting:
        setting.value = value
    else:
        setting = BotSetting(
            bot_id=bot.id,
            key=key,
            value=value
        )
        db.add(setting)

    db.commit()

    return {"success": True}

# =========================
# CREATE KNOWLEDGE
# =========================
@router.post("/api/knowledge/create")
async def create_knowledge(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    bot_id = form.get("bot_id")
    category = form.get("category")
    title = form.get("title")
    content = form.get("content")

    if not bot_id or not content:
        raise HTTPException(400, "bot_id & content wajib")

    bot = db.query(Bot).filter(
        Bot.id == int(bot_id),
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    item = BotKnowledge(
        bot_id=bot.id,
        category=category or "general",
        title=title,
        content=content
    )

    db.add(item)
    db.commit()

    return {
        "success": True
    }

# =========================
# GET KNOWLEDGE
# =========================
@router.get("/api/knowledge/list")
def list_knowledge(
    bot_id: int,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):

    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    items = db.query(BotKnowledge).filter(
        BotKnowledge.bot_id == bot.id
    ).order_by(BotKnowledge.id.desc()).all()

    return [
        {
            "id": x.id,
            "category": x.category,
            "title": x.title,
            "content": x.content
        }
        for x in items
    ]

# =========================
# UPDATE KNOWLEDGE
# =========================
@router.post("/api/knowledge/update")
async def update_knowledge(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    item_id = form.get("id")

    try:
        item_id = int(form.get("id"))
    except:
        raise HTTPException(400, "ID invalid")
    
    item = db.query(BotKnowledge).filter(
        BotKnowledge.id == int(item_id)
    ).first()

    if not item:
        raise HTTPException(404, "Knowledge tidak ditemukan")

    bot = db.query(Bot).filter(
        Bot.id == item.bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    item.category = form.get("category")
    item.title = form.get("title")
    item.content = form.get("content")

    db.commit()

    return {
        "success": True
    }

# =========================
# DELETE KNOWLEDGE
# =========================
@router.post("/api/knowledge/delete")
async def delete_knowledge(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    item_id = form.get("id")

    try:
        item_id = int(form.get("id"))
    except:
        raise HTTPException(400, "ID invalid")

    item = db.query(BotKnowledge).filter(
        BotKnowledge.id == int(item_id)
    ).first()

    if not item:
        raise HTTPException(404, "Knowledge tidak ditemukan")

    bot = db.query(Bot).filter(
        Bot.id == item.bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    db.delete(item)
    db.commit()

    return {
        "success": True
    }

# =========================
# CREATE FAQ
# =========================
@router.post("/api/faq/create")
async def create_faq(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    bot_id = form.get("bot_id")
    question = form.get("question")
    answer = form.get("answer")

    if not bot_id or not question or not answer:
        raise HTTPException(400, "Data belum lengkap")

    bot = db.query(Bot).filter(
        Bot.id == int(bot_id),
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    faq = BotFAQ(
        bot_id=bot.id,
        question=question,
        answer=answer
    )

    db.add(faq)
    db.commit()

    return {
        "success": True
    }

# =========================
# GET FAQ
# =========================
@router.get("/api/faq/list")
def list_faq(
    bot_id: int,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):

    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    items = db.query(BotFAQ).filter(
        BotFAQ.bot_id == bot.id
    ).order_by(BotFAQ.id.desc()).all()

    return [
        {
            "id": x.id,
            "question": x.question,
            "answer": x.answer
        }
        for x in items
    ]

# =========================
# UPDATE FAQ
# =========================
@router.post("/api/faq/update")
async def update_faq(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    faq_id = form.get("id")

    try:
        faq_id = int(form.get("id"))
    except:
        raise HTTPException(400, "ID invalid")

    faq = db.query(BotFAQ).filter(
        BotFAQ.id == int(faq_id)
    ).first()

    if not faq:
        raise HTTPException(404, "FAQ tidak ditemukan")

    bot = db.query(Bot).filter(
        Bot.id == faq.bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    faq.question = form.get("question")
    faq.answer = form.get("answer")

    db.commit()

    return {
        "success": True
    }

# =========================
# DELETE FAQ
# =========================
@router.post("/api/faq/delete")
async def delete_faq(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.json()

    faq_id = form.get("id")

    try:
        faq_id = int(form.get("id"))
    except:
        raise HTTPException(400, "ID invalid")

    faq = db.query(BotFAQ).filter(
        BotFAQ.id == int(faq_id)
    ).first()

    if not faq:
        raise HTTPException(404, "FAQ tidak ditemukan")

    bot = db.query(Bot).filter(
        Bot.id == faq.bot_id,
        Bot.owner_id == user.id
    ).first()

    if not bot:
        raise HTTPException(403, "Akses ditolak")

    db.delete(faq)
    db.commit()

    return {
        "success": True
    }