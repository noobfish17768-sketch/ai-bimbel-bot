#!/bin/sh

set -e

echo "================================="
echo "🚀 STARTING APPLICATION"
echo "================================="

# =========================
# WAIT DATABASE (ANTI CRASH)
# =========================
echo "⏳ Waiting for database..."

sleep 3

# =========================
# MIGRATION
# =========================
echo "🚀 Running migrations..."

alembic upgrade head || {
    echo "❌ Migration failed!"
    exit 1
}

echo "✅ Migrations completed"

# =========================
# SEED SETTINGS (OPTIONAL BUT IMPORTANT)
# =========================
echo "🌱 Seeding default settings..."

python scripts/seed_settings.py || {
    echo "⚠️ Seed skipped / failed (non critical)"
}

# =========================
# START APP
# =========================
echo "🚀 Starting FastAPI app..."

exec uvicorn app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-1}