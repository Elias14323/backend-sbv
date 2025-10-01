#!/usr/bin/env python3
"""Test Meilisearch integration with various queries."""

import asyncio
import sys
from pathlib import Path

import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_search():
    """Test search endpoint with various queries."""
    
    base_url = "http://localhost:8000/api/v1"
    
    test_queries = [
        ("Budget", "Search for 'Budget'"),
        ("Ukraine", "Search for 'Ukraine'"),
        ("maire", "Search for 'maire' (mayor in French)"),
        ("Marioupol", "Search for 'Marioupol'"),
        ("fashion", "Search for 'fashion'"),
        ("Chartres", "Search for 'Chartres'"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test health endpoint
        print("🏥 Testing search health endpoint...")
        response = await client.get(f"{base_url}/search/health")
        print(f"Response: {response.json()}\n")
        
        # Test searches
        for query, description in test_queries:
            print(f"🔍 {description}")
            response = await client.get(
                f"{base_url}/search",
                params={"q": query, "limit": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                processing_time = data.get("processingTimeMs", 0)
                total = data.get("estimatedTotalHits", 0)
                
                print(f"   ⏱️  Processing time: {processing_time}ms")
                print(f"   📊 Total results: {total}")
                print(f"   📄 Showing {len(hits)} results:")
                
                for i, hit in enumerate(hits, 1):
                    title = hit.get("title", "No title")
                    score = hit.get("_rankingScore", 0)
                    print(f"      {i}. [{score:.3f}] {title[:70]}...")
            else:
                print(f"   ❌ Error: {response.status_code}")
            
            print()
        
        # Test with language filter
        print("🔍 Search for 'Ukraine' with language filter (fr)")
        response = await client.get(
            f"{base_url}/search",
            params={"q": "Ukraine", "lang": "fr", "limit": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            print(f"   📊 Results: {len(hits)}")
            for i, hit in enumerate(hits, 1):
                title = hit.get("title", "No title")
                lang = hit.get("lang", "unknown")
                print(f"      {i}. [{lang}] {title[:70]}...")
        print()
        
        # Test typo tolerance
        print("🔍 Testing typo tolerance: 'Ukrain' (missing 'e')")
        response = await client.get(
            f"{base_url}/search",
            params={"q": "Ukrain", "limit": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            print(f"   📊 Results: {len(hits)} (should still find 'Ukraine')")
            for i, hit in enumerate(hits, 1):
                title = hit.get("title", "No title")
                print(f"      {i}. {title[:70]}...")
        print()


if __name__ == "__main__":
    print("🧪 Starting Meilisearch search tests...\n")
    asyncio.run(test_search())
    print("✅ Tests complete!")
