#!/usr/bin/env python3
"""Test the ingest_all_sources task."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.workers.tasks import ingest_all_sources

print("🧪 Testing ingest_all_sources task...")
print("")

result = ingest_all_sources.delay()
print(f"✅ Task triggered: {result.id}")
print(f"   Waiting for result...")

try:
    response = result.get(timeout=30)
    print(f"   Result: {response}")
except Exception as e:
    print(f"   ❌ Error: {e}")
