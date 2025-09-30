"""Trigger summary generation for a cluster."""

import sys

from app.workers.tasks import summarize_cluster

if __name__ == "__main__":
    cluster_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    
    print(f"Triggering summary generation for cluster {cluster_id}...")
    result = summarize_cluster.delay(cluster_id=cluster_id)
    print(f"Task sent with ID: {result.id}")
    print(f"Check logs with: tail -f /tmp/celery.log")
