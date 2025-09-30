"""Complete end-to-end test of event detection and SSE streaming."""

import asyncio
import json
import sys
import time

import httpx
import redis

from app.core.config import settings


async def sse_client():
    """SSE client that listens for events."""
    print("🔌 Connecting to SSE endpoint...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream('GET', 'http://localhost:8000/api/v1/stream/events') as response:
            print(f"✅ Connected (status {response.status_code})\n")
            
            print("📡 Listening for events (press Ctrl+C to stop)...\n")
            
            async for line in response.aiter_lines():
                if line.startswith('event:'):
                    event_type = line.split('event:', 1)[1].strip()
                    print(f"📨 Event type: {event_type}")
                elif line.startswith('data:'):
                    data = line.split('data:', 1)[1].strip()
                    try:
                        parsed = json.loads(data)
                        print(f"📦 Data: {json.dumps(parsed, indent=2)}\n")
                    except json.JSONDecodeError:
                        print(f"📦 Data: {data}\n")


async def publish_test_event(delay: float = 3.0):
    """Publish a test event after a delay."""
    await asyncio.sleep(delay)
    
    print(f"\n🚀 Publishing test event to Redis...\n")
    
    # Connect to Redis
    r = redis.Redis.from_url(settings.redis_url)
    
    # Create a test event
    test_event = {
        "event_id": 999,
        "cluster_id": 3,
        "severity": "critical",
        "label": "🔥 BREAKING: Test SSE Event",
        "score": 99.9,
        "detected_at": time.time(),
    }
    
    # Publish to events channel
    num_subscribers = r.publish("events", json.dumps(test_event))
    
    print(f"✅ Event published to {num_subscribers} subscriber(s)\n")
    
    r.close()


async def main():
    """Run SSE client and publisher concurrently."""
    try:
        # Start both tasks
        await asyncio.gather(
            sse_client(),
            publish_test_event(delay=2.0),
        )
    except KeyboardInterrupt:
        print("\n\n👋 Disconnected from SSE stream")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("SSE Event Streaming Test")
    print("=" * 60)
    print()
    
    asyncio.run(main())
