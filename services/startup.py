import os
import threading
from services.followup import run_followup

# =========================
# START FOLLOWUP THREAD (SAFE)
# =========================
def start_followup_worker():
    # ❗ prevent double thread
    if getattr(start_followup_worker, "_started", False):
        return

    start_followup_worker._started = True

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

    # ❗ HAPUS create_all (pakai Alembic saja)
    # Base.metadata.create_all(bind=engine)

    if os.getenv("ENABLE_FOLLOWUP") == "true":
        start_followup_worker()

    print("✅ SYSTEM READY")