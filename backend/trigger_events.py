"""Trigger trend calculation and event detection."""

from app.workers.tasks import calculate_trends, detect_events

if __name__ == "__main__":
    print("Triggering trend calculation...")
    trends_result = calculate_trends.delay()
    print(f"calculate_trends task sent with ID: {trends_result.id}")
    
    print("\nWaiting for trends calculation to complete...")
    print("(Check logs with: tail -f /tmp/celery.log)")
    print("\nAfter trends are calculated, run detect_events:")
    print("  python trigger_events.py --detect-only")
    
    # Uncomment to automatically detect events after trends:
    # import time
    # time.sleep(10)  # Wait for trends to complete
    # print("\nTriggering event detection...")
    # events_result = detect_events.delay()
    # print(f"detect_events task sent with ID: {events_result.id}")
