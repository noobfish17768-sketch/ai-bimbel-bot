#!/bin/bash

set -e  # 🔥 langsung stop kalau ada error
set -o pipefail

echo "================================="
echo "🚀 STARTING APPLICATION"
echo "================================="

# =========================
# START SERVER
# =========================
echo "🚀 Starting FastAPI app..."
echo "🔥 READY TO START UVICORN"
exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}