import os
import threading
from database.database import Base, engine
from services.followup import run_followup


# =========================
# INIT DB
# =========================
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")


# =========================
# START FOLLOWUP THREAD
# =========================
def start_followup_worker():
    thread = threading.Thread(
        target=run_followup,
        daemon=True
    )
    thread.start()
    print("🚀 Followup worker started")


# =========================
# MAIN STARTUP ENTRY
# =========================
def startup():
    print("🚀 STARTUP INIT")

    init_db()

    if os.getenv("ENABLE_FOLLOWUP") == "true":
        start_followup_worker()

    print("✅ SYSTEM READY")