#!/bin/bash
# Checks if any microservice improperly imports from the legacy 'app' package
# Excluding 'app.infrastructure.clients' and 'app.core' for now as they are shared libs temporarily

VIOLATIONS=$(grep -r "from app" microservices/ | grep -v "from app.infrastructure.clients" | grep -v "from app.core" | grep -v "test" || true)

if [ -n "$VIOLATIONS" ]; then
    echo "❌ Detected illegal imports from legacy 'app' package in microservices:"
    echo "$VIOLATIONS"
    exit 1
else
    echo "✅ No illegal 'from app' imports detected in microservices."
    exit 0
fi
