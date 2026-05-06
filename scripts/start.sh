#!/bin/bash

set -e  # 🔥 langsung stop kalau ada error
set -o pipefail

echo "================================="
echo "🚀 STARTING APPLICATION"
echo "================================="

# =========================
# WAIT DB (opsional)
# =========================
echo "⏳ Waiting for database..."
sleep 3

# =========================
# MIGRATIONS
# =========================
echo "🚀 Running migrations..."
alembic upgrade head || {
    echo "❌ MIGRATION FAILED"
    exit 1
}

# =========================
# SEED
# =========================
echo "🌱 Seeding..."
python scripts/seed_settings.py || {
    echo "❌ SEED FAILED"
    exit 1
}

# =========================
# START SERVER
# =========================
echo "🚀 Starting FastAPI app..."

exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}