from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from database.models import User
from core.dependencies import get_db
from core.security import get_current_user_db
from cache.cache import redis_client

router = APIRouter(prefix="/api/bot", tags=["bot"])


class ToggleRequest(BaseModel):
    status: bool


@router.post("/toggle")
def toggle_bot(
    request: Request,
    data: ToggleRequest,
    db=Depends(get_db)
):
    user_id = get_current_user_db(request)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.bot_active = data.status
        db.commit()
    except Exception as e:
        db.rollback()
        print("DB ERROR:", e)
        raise HTTPException(status_code=500, detail="Update failed")

    if redis_client:
        try:
            redis_client.set(
                f"bot:{user.id}",
                str(data.status),
                ex=3600  # cache 1 jam
            )
        except Exception as e:
            print("Redis error:", e)

    return {
        "success": True,
        "bot_active": data.status
    }