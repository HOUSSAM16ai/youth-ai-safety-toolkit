"""يتحقق من منع استيراد app داخل الميكروسيرفس مع نمط تحذير/فشل تدريجي."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MICROSERVICES_ROOT = REPO_ROOT / "microservices"


def _find_violations() -> list[str]:
    violations: list[str] = []
    for file_path in MICROSERVICES_ROOT.rglob("*.py"):
        if "tests" in file_path.parts:
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=file_path.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app" or module.startswith("app."):
                    violations.append(f"{file_path}:{node.lineno} from {module} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if module == "app" or module.startswith("app."):
                        violations.append(f"{file_path}:{node.lineno} import {module}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="يفشل الفحص عند وجود مخالفات.")
    args = parser.parse_args()

    violations = _find_violations()
    if not violations:
        print("✅ No 'from app' imports found inside microservices.")
        return 0

    print("⚠️ Detected app imports in microservices:")
    for violation in violations:
        print(f" - {violation}")

    if args.strict:
        print("❌ Strict mode enabled: app imports are forbidden.")
        return 1

    print("⚠️ Warn mode: this does not fail CI yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
