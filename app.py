from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

import os

from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.settings import router as settings_router
from routes.bot import router as bot_router
from routes.leads import router as leads_router
from bot.webhook import router as webhook_router
from routes.conversations import router as conv_router
from routes.admin import router as admin_router

print("🚀 START APP")

app = FastAPI()

# =========================
# SESSION
# =========================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    https_only=True,
    same_site="lax"
)

# =========================
# ROUTES
# =========================
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(bot_router)
app.include_router(leads_router)
app.include_router(webhook_router)
app.include_router(conv_router)
app.include_router(admin_router)

# =========================
# STATIC
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "alive 🚀"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")