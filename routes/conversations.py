from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from database.models import Conversation
from core.dependencies import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/conversations")
def conversations(request: Request, db=Depends(get_db)):

    chats = db.query(Conversation).order_by(Conversation.id.desc()).limit(100).all()

    return templates.TemplateResponse(
        "conversations.html",
        {
            "request": request,
            "chats": chats
        }
    )