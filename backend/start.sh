#!/bin/bash
# Start complete Backend SBV system in development mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Backend SBV Complete System"
echo "========================================"
echo ""

# Check if services are already running
echo "🔍 Checking existing services..."

# Kill existing processes
pkill -f "meilisearch" 2>/dev/null || true
pkill -f "celery -A app.workers.celery_app" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 2

echo ""
echo "📦 Starting services..."
echo ""

# Start Meilisearch
echo "1️⃣  Starting Meilisearch..."
nohup meilisearch --master-key devMasterKey123 --http-addr localhost:7700 > /tmp/meilisearch.log 2>&1 &
sleep 2
echo "   ✅ Meilisearch running on port 7700"

# Start Celery Worker
echo ""
echo "2️⃣  Starting Celery Worker..."
cd "$SCRIPT_DIR"
nohup poetry run celery -A app.workers.celery_app worker --loglevel=info > /tmp/celery-worker.log 2>&1 &
sleep 3
echo "   ✅ Celery Worker running"

# Start Celery Beat (scheduler)
echo ""
echo "3️⃣  Starting Celery Beat (scheduler)..."
nohup poetry run celery -A app.workers.celery_app beat --loglevel=info > /tmp/celery-beat.log 2>&1 &
sleep 2
echo "   ✅ Celery Beat running"

# Start FastAPI
echo ""
echo "4️⃣  Starting FastAPI..."
nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/api.log 2>&1 &
sleep 3
echo "   ✅ FastAPI running on port 8000"

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📊 Service URLs:"
echo "   API:         http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Meilisearch: http://localhost:7700"
echo ""
echo "📝 Log files:"
echo "   API:          tail -f /tmp/api.log"
echo "   Worker:       tail -f /tmp/celery-worker.log"
echo "   Beat:         tail -f /tmp/celery-beat.log"
echo "   Meilisearch:  tail -f /tmp/meilisearch.log"
echo ""
echo "📅 Scheduled tasks:"
echo "   - Ingest all sources: every 15 minutes"
echo "   - Calculate trends:   every 5 minutes"
echo "   - Detect events:      triggered after trends"
echo ""
echo "🛑 To stop all services: ./stop.sh"
