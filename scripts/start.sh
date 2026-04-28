#!/bin/sh

set -e

echo "================================="
echo "🚀 STARTING APPLICATION"
echo "================================="

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
# START APP
# =========================
echo "🚀 Starting FastAPI app..."

exec uvicorn app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000}