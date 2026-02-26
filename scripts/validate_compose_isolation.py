"""يتحقق من عزل سياقات البناء ومنع ربط المستودع بالكامل في ملفات التشغيل."""

from __future__ import annotations

import argparse
from pathlib import Path

ALLOWED_CONTEXTS: dict[str, dict[str, str]] = {
    "docker-compose.yml": {
        "frontend": "./frontend",
        "orchestrator-service": "./microservices/orchestrator_service",
        "observability-service": "./microservices/observability_service",
        "planning-agent": "./microservices/planning_agent",
        "memory-agent": "./microservices/memory_agent",
        "user-service": "./microservices/user_service",
    },
    "docker-compose.legacy.yml": {
        "core-kernel": ".",
    },
}

PROHIBITED_VOLUME_TOKENS = {
    ".:/app",
    "${PWD}:/app",
}


def _parse_contexts(compose_path: Path) -> dict[str, str]:
    """يستخرج سياقات البناء لكل خدمة من ملف تشغيل."""
    contexts: dict[str, str] = {}
    current_service: str | None = None
    in_build_block = False
    for raw_line in compose_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.strip().endswith(":") and not line.lstrip().startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent == 2 and line.strip() not in {"services:", "networks:", "volumes:"}:
                current_service = line.strip().removesuffix(":")
                in_build_block = False
                continue
        if current_service is None:
            continue
        stripped = line.strip()
        if stripped.startswith("build:"):
            in_build_block = True
            continue
        if in_build_block and stripped.startswith("context:"):
            contexts[current_service] = stripped.removeprefix("context:").strip()
            continue
        if (
            in_build_block
            and stripped
            and not stripped.startswith("#")
            and ":" in stripped
            and stripped.split(":", 1)[0] != "context"
            and stripped.split(":", 1)[0] != "dockerfile"
        ):
            in_build_block = False
        if stripped.startswith("volumes:") or stripped.startswith("environment:"):
            in_build_block = False
    return contexts


def _find_prohibited_volumes(compose_path: Path) -> list[str]:
    """يرصد أي ربط محظور للمستودع داخل الحاويات."""
    violations: list[str] = []
    for idx, raw_line in enumerate(compose_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("- "):
            token = line.removeprefix("- ").strip()
            if token in PROHIBITED_VOLUME_TOKENS:
                violations.append(f"{compose_path}:{idx}: {token}")
    return violations


def _validate_contexts(compose_path: Path, allowed: dict[str, str]) -> list[str]:
    """يتحقق من تطابق سياقات البناء مع السياسة المسموحة."""
    found = _parse_contexts(compose_path)
    violations: list[str] = []
    for service_name, expected_context in allowed.items():
        actual_context = found.get(service_name)
        if actual_context is None:
            violations.append(f"{compose_path}: missing context for {service_name}")
            continue
        if actual_context != expected_context:
            violations.append(
                f"{compose_path}: {service_name} context '{actual_context}' != '{expected_context}'"
            )
    return violations


def _collect_violations() -> list[str]:
    """يجمع كل الانحرافات عن سياسة العزل في ملفات التشغيل."""
    violations: list[str] = []
    for filename, allowed in ALLOWED_CONTEXTS.items():
        compose_path = Path(filename)
        if not compose_path.exists():
            violations.append(f"missing compose file: {compose_path}")
            continue
        violations.extend(_validate_contexts(compose_path, allowed))
        violations.extend(_find_prohibited_volumes(compose_path))
    return violations


def main() -> int:
    """يشغل فحص العزل ويعيد رمز خروج مناسب."""
    parser = argparse.ArgumentParser(description="Validate compose isolation rules.")
    _ = parser.parse_args()
    violations = _collect_violations()
    if violations:
        print("Isolation validation failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Isolation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
