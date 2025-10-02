#!/bin/bash
# Stop all Backend SBV services

echo "🛑 Stopping Backend SBV services..."
echo ""

echo "Stopping FastAPI..."
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "   ✅ FastAPI stopped" || echo "   ℹ️  FastAPI not running"

echo "Stopping Celery Beat..."
pkill -f "celery -A app.workers.celery_app beat" 2>/dev/null && echo "   ✅ Celery Beat stopped" || echo "   ℹ️  Celery Beat not running"

echo "Stopping Celery Worker..."
pkill -f "celery -A app.workers.celery_app worker" 2>/dev/null && echo "   ✅ Celery Worker stopped" || echo "   ℹ️  Celery Worker not running"

echo "Stopping Meilisearch..."
pkill -f "meilisearch" 2>/dev/null && echo "   ✅ Meilisearch stopped" || echo "   ℹ️  Meilisearch not running"

echo ""
echo "✅ All services stopped"
