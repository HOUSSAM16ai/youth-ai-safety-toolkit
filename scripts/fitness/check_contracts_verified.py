"""يتحقق من اكتمال خط أساس العقود ويشغّل تحقق المزود الفعلي لضمان السلامة."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_FILE = REPO_ROOT / "docs/contracts/consumer/gateway_route_contracts.json"
TEST_FILE = REPO_ROOT / "tests/contracts/test_gateway_routing_contracts.py"
CHAT_CONTENT_CONTRACT_FILE = (
    REPO_ROOT / "docs/contracts/consumer/gateway_chat_content_contracts.json"
)
VERSIONING_RULES_FILE = REPO_ROOT / "docs/contracts/consumer/gateway_versioning_rules.md"
PROVIDER_TEST_FILE = REPO_ROOT / "tests/contracts/test_gateway_provider_contracts.py"
PROVIDER_SCRIPT = REPO_ROOT / "scripts/fitness/check_gateway_provider_contracts.py"


def _run_command(command: list[str]) -> bool:
    """يشغّل أمر تحقق ويعيد نجاحه مع طباعة التشخيص عند الفشل."""
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    print("❌ Command failed:", " ".join(command))
    print(result.stdout.strip())
    print(result.stderr.strip())
    return False


def main() -> int:
    """يتحقق من الملفات المطلوبة ثم ينفذ تحقق عقد المزود الاختباري."""
    if not CONTRACT_FILE.exists():
        print("❌ Missing gateway consumer contract file.")
        return 1
    if not TEST_FILE.exists():
        print("❌ Missing gateway routing contract test.")
        return 1
    if not CHAT_CONTENT_CONTRACT_FILE.exists():
        print("❌ Missing gateway chat/content provider contract file.")
        return 1
    if not VERSIONING_RULES_FILE.exists():
        print("❌ Missing gateway versioning rules documentation.")
        return 1
    if not PROVIDER_TEST_FILE.exists():
        print("❌ Missing gateway provider contract test.")
        return 1

    data = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
    contracts = data.get("contracts", [])
    required_routes = {
        "/api/chat/{path:path}",
        "/v1/content/{path:path}",
        "/api/v1/data-mesh/{path:path}",
        "/system/{path:path}",
    }
    current_routes = {item.get("route") for item in contracts}
    if not required_routes.issubset(current_routes):
        print("❌ Contract baseline incomplete for cutover routes (phase1/phase2).")
        return 1

    if not _run_command(["python", str(PROVIDER_SCRIPT)]):
        return 1
    if not _run_command(["python", "-m", "pytest", "-q", str(PROVIDER_TEST_FILE)]):
        return 1

    print("✅ Contract baseline + provider verification runtime checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
