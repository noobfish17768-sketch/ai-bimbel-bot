from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database.models import BotSetting, Bot
from core.dependencies import get_db
from core.security import get_current_user_web, get_current_user_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "bot_id": bot.id
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


@router.post("/api/settings")
async def update_setting(
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user_db)
):
    form = await request.form()

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