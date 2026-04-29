from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from database.models import Conversation, User
from core.dependencies import get_db
from core.security import get_current_user_web

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/conversations")
def conversations(request: Request, db=Depends(get_db)):

    user = get_current_user_web(request)

    # kalau belum login → redirect
    if not hasattr(user, "id"):
        return user

    chats = db.query(Conversation)\
        .filter(Conversation.user_id == str(user.id))\
        .order_by(Conversation.id.desc())\
        .limit(100)\
        .all()

    return templates.TemplateResponse(
        "conversations.html",
        {
            "request": request,
            "chats": chats,
            "user_id": user.id
        }
    )