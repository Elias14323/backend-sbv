"""Script to trigger ingestion of a source."""

from app.workers.tasks import ingest_source


def trigger() -> None:
    """Trigger ingestion for source ID=1 (Le Monde)."""
    print("🔥 Déclenchement de l'ingestion pour la source ID=1 (Le Monde)...")
    
    # Call task directly (will be routed to Celery queue)
    result = ingest_source.delay(1)
    
    print(f"✅ Tâche envoyée ! Task ID: {result.id}")
    print("📊 Surveille le worker Celery pour voir les logs...")


if __name__ == "__main__":
    trigger()
