#!/bin/bash
# Check status of Backend SBV services

echo "📊 Backend SBV Service Status"
echo "=============================="
echo ""

check_service() {
    local name=$1
    local pattern=$2
    
    if pgrep -f "$pattern" > /dev/null; then
        echo "✅ $name: RUNNING"
        return 0
    else
        echo "❌ $name: STOPPED"
        return 1
    fi
}

check_service "Meilisearch" "meilisearch"
check_service "Celery Worker" "celery -A app.workers.celery_app worker"
check_service "Celery Beat" "celery -A app.workers.celery_app beat"
check_service "FastAPI" "uvicorn app.main:app"

echo ""
echo "🔍 Quick Health Checks:"
echo ""

# Check API
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ API responding on http://localhost:8000"
else
    echo "❌ API not responding"
fi

# Check Meilisearch
if curl -s http://localhost:7700/health > /dev/null 2>&1; then
    echo "✅ Meilisearch responding on http://localhost:7700"
else
    echo "❌ Meilisearch not responding"
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis responding"
else
    echo "❌ Redis not responding"
fi

echo ""
echo "📝 Recent logs:"
echo "   Worker: tail -20 /tmp/celery-worker.log"
echo "   Beat:   tail -20 /tmp/celery-beat.log"
