"""Celery application configuration."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "backend_sbv",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule configuration
celery_app.conf.beat_schedule = {
    # Ingest all sources every 15 minutes
    "ingest-all-sources-every-15-minutes": {
        "task": "tasks.ingest_all_sources",
        "schedule": 900.0,  # 15 minutes in seconds
        "options": {"expires": 600},  # Task expires after 10 minutes if not picked up
    },
    # Calculate trends every 5 minutes
    "calculate-trends-every-5-minutes": {
        "task": "tasks.calculate_trends",
        "schedule": 300.0,  # 5 minutes in seconds
        "options": {"expires": 240},  # Task expires after 4 minutes if not picked up
    },
}

# Make tasks discoverable
celery_app.autodiscover_tasks(["app.workers"])

# Expose the Celery app instance
app = celery_app

__all__ = ["celery_app", "app"]
