#!/bin/bash
# scripts/check_app_imports.sh
# Fails if "from app" or "import app" is found in microservices/, excluding allowlisted files.
# Only scans .py files to avoid false positives in documentation.

set -e

# Temporary allowlist for existing violations (will be removed in PR #4)
# We only allow conftest.py as it needs app fixture for now (until we mock it fully)
ALLOWLIST="microservices/user_service/tests/conftest.py"

echo "Scanning for 'from app' or 'import app' in microservices/..."

# Find all python files in microservices
VIOLATIONS=$(grep -rE --include="*.py" "^\s*(from|import)\s+app\b" microservices | grep -vE "$ALLOWLIST" || true)

if [ -n "$VIOLATIONS" ]; then
    echo "❌ ERROR: Found forbidden imports from 'app' package in microservices:"
    echo "$VIOLATIONS"
    echo ""
    echo "Microservices must be independent and cannot import from the monolith 'app/' namespace."
    exit 1
else
    echo "✅ No new forbidden imports found."
    exit 0
fi
