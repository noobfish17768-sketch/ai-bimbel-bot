from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database.models import BotSetting
from core.dependencies import get_db
from core.security import get_current_user_web, get_current_user_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/settings")
def settings_page(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request)

    # kalau redirect (belum login)
    if not hasattr(user, "id"):
        return user

    settings = db.query(BotSetting).filter(
        BotSetting.user_id == str(user.id)
    ).all()

    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": settings}
    )


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.post("/api/settings")
def update_setting(request: Request, data: SettingUpdate, db=Depends(get_db)):

    user_id = get_current_user_db(request)

    setting = db.query(BotSetting).filter(
        BotSetting.user_id == str(user_id),
        BotSetting.key == data.key
    ).first()

    if setting:
        setting.value = data.value
    else:
        setting = BotSetting(
            user_id=str(user_id),
            key=data.key,
            value=data.value
        )
        db.add(setting)

    db.commit()

    return {"success": True}