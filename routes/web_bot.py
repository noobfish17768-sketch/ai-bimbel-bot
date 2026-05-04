from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from core.dependencies import get_db
from core.security import get_current_user_web

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/create-bot")
def create_bot_page(request: Request, db=Depends(get_db)):
    user = get_current_user_web(request, db)

    if not hasattr(user, "id"):
        return user

    return templates.TemplateResponse("create_bot.html", {
        "request": request
    })