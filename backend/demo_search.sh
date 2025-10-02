#!/bin/bash
# Demo script showing Meilisearch integration

echo "🔍 Backend SBV - Meilisearch Search Demo"
echo "========================================"
echo ""

echo "📊 Index Statistics:"
curl -s -H "Authorization: Bearer devMasterKey123" "http://localhost:7700/indexes/articles/stats" | python3 -m json.tool
echo ""

echo "🔍 Test 1: Search for 'Ukraine'"
curl -s "http://localhost:8000/api/v1/search?q=Ukraine&limit=3" | python3 -m json.tool | grep -E "(query|estimatedTotalHits|title)" | head -10
echo ""

echo "�� Test 2: Search with typo 'Ukrain' (missing e)"
curl -s "http://localhost:8000/api/v1/search?q=Ukrain&limit=2" | python3 -m json.tool | grep -E "(query|estimatedTotalHits|title)" | head -8
echo ""

echo "🔍 Test 3: Search for 'Budget'"
curl -s "http://localhost:8000/api/v1/search?q=Budget&limit=2" | python3 -m json.tool | grep -E "(query|estimatedTotalHits|title)" | head -8
echo ""

echo "✅ Search system operational!"
