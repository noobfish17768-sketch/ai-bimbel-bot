#!/bin/sh

set -e

echo "🚀 Running migrations..."
alembic upgrade head

echo "🚀 Starting app..."
exec uvicorn app:app --host 0.0.0.0 --port $PORT