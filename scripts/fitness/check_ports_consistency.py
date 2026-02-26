"""يفحص اتساق المنافذ بين compose وMakefile ووثيقة مصدر الحقيقة."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PORTS_FILE = REPO_ROOT / "docs/architecture/PORTS_SOURCE_OF_TRUTH.json"
DOCKER_COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKER_COMPOSE_LEGACY = REPO_ROOT / "docker-compose.legacy.yml"
MAKEFILE = REPO_ROOT / "Makefile"


def _contains_port(file_path: Path, port: int) -> bool:
    content = file_path.read_text(encoding="utf-8")
    same_token = f'"{port}:{port}"'
    host_token = f'"{port}:'
    return same_token in content or host_token in content or f"localhost:{port}" in content


def main() -> int:
    ports = json.loads(PORTS_FILE.read_text(encoding="utf-8"))
    api_gateway_port = ports["api_gateway"]
    core_kernel_port = ports["core_kernel"]

    if not _contains_port(DOCKER_COMPOSE, api_gateway_port):
        print(f"❌ Missing api_gateway port {api_gateway_port} in docker-compose.yml")
        return 1
    if _contains_port(DOCKER_COMPOSE, core_kernel_port):
        print(
            f"❌ core_kernel port {core_kernel_port} must not appear in default docker-compose.yml"
        )
        return 1

    if not _contains_port(DOCKER_COMPOSE_LEGACY, core_kernel_port):
        print(f"❌ Missing core_kernel port {core_kernel_port} in docker-compose.legacy.yml")
        return 1

    for port in (api_gateway_port, core_kernel_port):
        if not _contains_port(MAKEFILE, port):
            print(f"❌ Missing port {port} in Makefile")
            return 1

    print("✅ Port consistency check passed (default excludes core-kernel, legacy retains it).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
