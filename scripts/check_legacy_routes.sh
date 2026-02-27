#!/bin/bash
# scripts/check_legacy_routes.sh
# Fails if legacy routes increase above 5.

set -e

# Baseline number of legacy routes
BASELINE=5

echo "Scanning for legacy routes in microservices/api_gateway/main.py..."

# Count lines with "deprecated=True" in api_gateway/main.py
CURRENT=$(grep "deprecated=True" microservices/api_gateway/main.py | wc -l)

echo "Found $CURRENT legacy routes (Baseline: $BASELINE)."

if [ "$CURRENT" -gt "$BASELINE" ]; then
    echo "❌ ERROR: Legacy routes increased from $BASELINE to $CURRENT."
    echo "Adding new legacy routes is forbidden. Please implement new routes in microservices."
    exit 1
elif [ "$CURRENT" -lt "$BASELINE" ]; then
    echo "🎉 SUCCESS: Legacy routes decreased! Update the baseline in this script."
    # We could exit 1 here to force updating the script, but for now we just warn.
    exit 0
else
    echo "✅ Legacy routes count is stable."
    exit 0
fi
