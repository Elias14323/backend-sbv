"""Test SSE event streaming by publishing a test event to Redis."""

import json
import sys
import time

import redis

from app.core.config import settings

if __name__ == "__main__":
    # Connect to Redis
    r = redis.Redis.from_url(settings.redis_url)
    
    # Create a test event
    test_event = {
        "event_id": 999,
        "cluster_id": 3,
        "severity": "high",
        "label": "TEST EVENT - SSE Streaming Test",
        "score": 99.9,
        "detected_at": time.time(),
    }
    
    print(f"Publishing test event to Redis channel 'events':")
    print(json.dumps(test_event, indent=2))
    
    # Publish to events channel
    num_subscribers = r.publish("events", json.dumps(test_event))
    
    print(f"\n✅ Event published to {num_subscribers} subscriber(s)")
    
    if num_subscribers == 0:
        print("\n⚠️  No subscribers connected. Start an SSE client first:")
        print("   curl -N http://localhost:8000/api/v1/stream/events")
        sys.exit(1)
    
    r.close()
