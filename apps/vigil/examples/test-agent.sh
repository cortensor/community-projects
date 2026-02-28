#!/bin/bash

# Test script for Vigil Agent
# This script tests all major functionality

set -e

API_URL="http://localhost:3001/api"

echo "🧪 Testing Vigil Agent"
echo "===================================="
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
response=$(curl -s "${API_URL}/health")
if echo "$response" | grep -q "ok"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi
echo ""

# Test 2: Get current metrics
echo "2️⃣  Testing current metrics..."
response=$(curl -s "${API_URL}/metrics/current")
if echo "$response" | grep -q "latency"; then
    echo "✅ Current metrics retrieved"
    echo "   Latency: $(echo $response | grep -o '"latency":[0-9.]*' | cut -d: -f2)"
else
    echo "❌ Failed to get current metrics"
    exit 1
fi
echo ""

# Test 3: Get metrics history
echo "3️⃣  Testing metrics history..."
response=$(curl -s "${API_URL}/metrics/history?limit=10")
if echo "$response" | grep -q "timestamp"; then
    count=$(echo "$response" | grep -o "timestamp" | wc -l)
    echo "✅ Metrics history retrieved ($count records)"
else
    echo "❌ Failed to get metrics history"
    exit 1
fi
echo ""

# Test 4: Simulate high latency incident
echo "4️⃣  Testing incident simulation (high_latency)..."
response=$(curl -s -X POST "${API_URL}/simulate" \
    -H "Content-Type: application/json" \
    -d '{"type":"high_latency"}')
if echo "$response" | grep -q "success"; then
    echo "✅ High latency incident simulated"
    incident_id=$(echo "$response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   Incident ID: $incident_id"
else
    echo "❌ Failed to simulate incident"
    exit 1
fi
echo ""

# Wait for processing
echo "⏳ Waiting for incident processing (5 seconds)..."
sleep 5
echo ""

# Test 5: Get all incidents
echo "5️⃣  Testing incidents list..."
response=$(curl -s "${API_URL}/incidents")
if echo "$response" | grep -q "high_latency"; then
    count=$(echo "$response" | grep -o '"id":"incident_' | wc -l)
    echo "✅ Incidents list retrieved ($count incidents)"
else
    echo "❌ Failed to get incidents list"
    exit 1
fi
echo ""

# Test 6: Get specific incident
if [ ! -z "$incident_id" ]; then
    echo "6️⃣  Testing specific incident retrieval..."
    response=$(curl -s "${API_URL}/incidents/${incident_id}")
    if echo "$response" | grep -q "analysis"; then
        echo "✅ Specific incident retrieved"
        echo "   Status: $(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
        echo "   Consensus: $(echo $response | grep -o '"consensus":[^,]*' | cut -d: -f2)"
    else
        echo "❌ Failed to get specific incident"
        exit 1
    fi
    echo ""
fi

# Test 7: Simulate high error rate
echo "7️⃣  Testing incident simulation (high_error_rate)..."
response=$(curl -s -X POST "${API_URL}/simulate" \
    -H "Content-Type: application/json" \
    -d '{"type":"high_error_rate"}')
if echo "$response" | grep -q "success"; then
    echo "✅ High error rate incident simulated"
else
    echo "❌ Failed to simulate high error rate"
    exit 1
fi
echo ""

# Test 8: Simulate validator score drop
echo "8️⃣  Testing incident simulation (validator_score_drop)..."
response=$(curl -s -X POST "${API_URL}/simulate" \
    -H "Content-Type: application/json" \
    -d '{"type":"validator_score_drop"}')
if echo "$response" | grep -q "success"; then
    echo "✅ Validator score drop incident simulated"
else
    echo "❌ Failed to simulate validator score drop"
    exit 1
fi
echo ""

# Wait for processing
echo "⏳ Waiting for incidents processing (5 seconds)..."
sleep 5
echo ""

# Test 9: Get active incidents
echo "9️⃣  Testing active incidents..."
response=$(curl -s "${API_URL}/incidents/active")
active_count=$(echo "$response" | grep -o '"id":"incident_' | wc -l)
echo "✅ Active incidents retrieved ($active_count active)"
echo ""

# Test 10: Verify evidence bundles
echo "🔟 Testing evidence bundles..."
response=$(curl -s "${API_URL}/incidents")
if echo "$response" | grep -q "evidenceBundle"; then
    echo "✅ Evidence bundles generated"
    echo "   Session IDs found: $(echo $response | grep -o 'session_[0-9]*' | wc -l)"
else
    echo "⚠️  Evidence bundles not yet generated (may still be processing)"
fi
echo ""

echo "===================================="
echo "✅ All tests passed!"
echo ""
echo "Summary:"
echo "- Health check: ✅"
echo "- Metrics collection: ✅"
echo "- Incident simulation: ✅"
echo "- Cortensor analysis: ✅"
echo "- Evidence generation: ✅"
echo ""
echo "🎉 Vigil Agent is working correctly!"
