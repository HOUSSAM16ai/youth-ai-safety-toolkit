"""يبني لوحة تقدم القطع (Cutover Scoreboard) عبر قياسات آلية قابلة للتتبع."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"
SCOREBOARD_MD = REPO_ROOT / "docs/diagnostics/CUTOVER_SCOREBOARD.md"
CONTRACT_GATE_SCRIPT = REPO_ROOT / "scripts/fitness/check_contracts_verified.py"
TRACING_GATE_SCRIPT = REPO_ROOT / "scripts/fitness/check_tracing_gate.py"
DOCS_RUNTIME_PARITY_SCRIPT = REPO_ROOT / "scripts/fitness/check_docs_runtime_parity.py"
BREAKGLASS_GATE_SCRIPT = REPO_ROOT / "scripts/fitness/check_breakglass_expiry_enforcement.py"
OVERMIND_COUPLING_GATE_SCRIPT = REPO_ROOT / "scripts/fitness/check_overmind_copy_coupling.py"
OVERMIND_BASELINE_FILE = REPO_ROOT / "config/overmind_copy_coupling_baseline.json"
MICROSERVICE_CATALOG_FILE = REPO_ROOT / "config/microservice_catalog.json"


def _count_app_imports_in_microservices() -> int:
    violations = 0
    for file_path in (REPO_ROOT / "microservices").rglob("*.py"):
        if "tests" in file_path.parts:
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=file_path.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app" or module.startswith("app."):
                    violations += 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if module == "app" or module.startswith("app."):
                        violations += 1
    return violations


def _copy_overlap_metric() -> int:
    app_root = REPO_ROOT / "app/services/overmind"
    ms_root = REPO_ROOT / "microservices/orchestrator_service/src/services/overmind"
    app_files = {p.relative_to(app_root).as_posix() for p in app_root.rglob("*") if p.is_file()}
    ms_files = {p.relative_to(ms_root).as_posix() for p in ms_root.rglob("*") if p.is_file()}
    return len(app_files & ms_files)


def _service_lifecycle_drift() -> list[str]:
    """يشتق انحراف دورة الحياة من كتالوج الخدمات الرسمي بدل المسح العشوائي."""
    compose_text = DEFAULT_COMPOSE.read_text(encoding="utf-8")
    catalog = json.loads(MICROSERVICE_CATALOG_FILE.read_text(encoding="utf-8"))
    drifts: list[str] = []
    for entry in catalog["services"]:
        service_name = str(entry["service_dir"])
        compose_service = str(entry["compose_service"])
        dockerfile_required = bool(entry["dockerfile_required"])
        expected_in_default_compose = bool(entry["expected_in_default_compose"])

        service_path = REPO_ROOT / "microservices" / service_name
        if not service_path.exists() or not service_path.is_dir():
            drifts.append(f"{service_name}:missing_directory")
            continue

        if dockerfile_required and not (service_path / "Dockerfile").exists():
            drifts.append(f"{service_name}:missing_dockerfile")

        compose_token_present = f"{compose_service}:" in compose_text
        if expected_in_default_compose and not compose_token_present:
            drifts.append(f"{service_name}:missing_compose_registration")
        if not expected_in_default_compose and compose_token_present:
            drifts.append(f"{service_name}:unexpected_compose_registration")
    return drifts


def _run_gate(script_path: Path) -> bool:
    """يشغّل بوابة لياقة منفصلة ويعيد حالة النجاح دون رفع استثناء."""
    result = subprocess.run(
        ["python", str(script_path)], cwd=REPO_ROOT, check=False, capture_output=True
    )
    return result.returncode == 0


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    routes: list[dict[str, object]] = registry["routes"]
    default_routes = [item for item in routes if bool(item.get("default_profile", False))]
    legacy_default = [item for item in default_routes if bool(item.get("legacy_target", False))]
    ws_legacy_default = [item for item in legacy_default if item.get("protocol") == "websocket"]

    default_text = DEFAULT_COMPOSE.read_text(encoding="utf-8")
    core_kernel_in_default_profile = (
        "core-kernel:" in default_text or "postgres-core:" in default_text
    )
    emergency_legacy_expiry_enforced = _run_gate(BREAKGLASS_GATE_SCRIPT)

    app_import_count = _count_app_imports_in_microservices()
    overlap_metric = _copy_overlap_metric()
    lifecycle_drift = _service_lifecycle_drift()
    docs_runtime_parity = _run_gate(DOCS_RUNTIME_PARITY_SCRIPT)
    contract_gate = _run_gate(CONTRACT_GATE_SCRIPT)
    tracing_gate = _run_gate(TRACING_GATE_SCRIPT)
    overmind_coupling_gate = _run_gate(OVERMIND_COUPLING_GATE_SCRIPT)
    overmind_policy = json.loads(OVERMIND_BASELINE_FILE.read_text(encoding="utf-8"))
    overmind_phase = str(overmind_policy.get("phase", "unknown"))
    overmind_mode = str(overmind_policy.get("policy", "unknown"))

    content = """# Cutover Scoreboard

## Current metrics
| metric | value |
|---|---:|
| legacy_routes_count | {legacy_routes_count} |
| ws_legacy_targets_count | {ws_legacy_targets_count} |
| core_kernel_in_default_profile | {core_kernel_in_default_profile} |
| emergency_legacy_expiry_enforced | {emergency_legacy_expiry_enforced} |
| app_import_count_in_microservices | {app_import_count_in_microservices} |
| active_copy_coupling_overlap_metric | {active_copy_coupling_overlap_metric} |
| docs_runtime_parity | {docs_runtime_parity} |
| contract_gate | {contract_gate} |
| tracing_gate | {tracing_gate} |

## Phase 0 forensic baseline inventory

### 1) Split-brain sources
- Runtime default topology is microservices-only (`docker-compose.yml`), while emergency legacy is isolated in `docker-compose.legacy.yml`.
- Documentation existed in markdown-only registry; machine-readable authority is now `config/route_ownership_registry.json`.
- Developer startup paths still include monolith-era helpers (`scripts/start.sh`, `scripts/start-backend.sh`) and require controlled retirement in later phases.

### 2) Gateway compatibility surfaces
- HTTP compatibility routes inventoried from `config/route_ownership_registry.json`.
- WebSocket compatibility routes: `/api/chat/ws`, `/admin/api/chat/ws`.

### 3) Phantom-limb coupling
- Import edges (`from app` داخل microservices): **{app_import_count_in_microservices}**.
- Copy-coupling overlap (`app/services/overmind` vs `microservices/orchestrator_service/src/services/overmind`): **{active_copy_coupling_overlap_metric}** shared files.
- Overmind coupling gate (phase {overmind_phase} / {overmind_mode}): **{overmind_coupling_gate}**.

### 4) Service lifecycle drift
{lifecycle_drift_lines}
""".format(
        legacy_routes_count=len(legacy_default),
        ws_legacy_targets_count=len(ws_legacy_default),
        core_kernel_in_default_profile=str(core_kernel_in_default_profile).lower(),
        emergency_legacy_expiry_enforced=str(emergency_legacy_expiry_enforced).lower(),
        app_import_count_in_microservices=app_import_count,
        active_copy_coupling_overlap_metric=overlap_metric,
        docs_runtime_parity=str(docs_runtime_parity).lower(),
        contract_gate=str(contract_gate).lower(),
        tracing_gate=str(tracing_gate).lower(),
        overmind_coupling_gate=str(overmind_coupling_gate).lower(),
        overmind_phase=overmind_phase,
        overmind_mode=overmind_mode,
        lifecycle_drift_lines="\n".join(f"- {item}" for item in lifecycle_drift)
        if lifecycle_drift
        else "- No lifecycle drift detected in Dockerfile + compose registration checks.",
    )

    SCOREBOARD_MD.write_text(content, encoding="utf-8")
    print(f"✅ Generated {SCOREBOARD_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
