import ast
import os
import sys
import pytest

# Add repo root to path to ensure imports work if needed (though we use AST)
sys.path.append(os.getcwd())

GATEWAY_FILE = "microservices/api_gateway/main.py"

# These functions are allowed to point to the Monolith (for now).
# Any NEW function added to this list violates the "Stop the Bleeding" rule.
LEGACY_ALLOWLIST = {
    "admin_ai_config_proxy",
    "chat_http_proxy",
    "chat_ws_proxy",
    "admin_chat_ws_proxy",
    "content_proxy",
    "datamesh_proxy",
    "system_proxy",
}

@pytest.fixture(autouse=True)
def db_lifecycle():
    """Override global fixture to avoid DB connection for this static analysis test."""
    yield

def test_gateway_route_freeze():
    """
    GOVERNANCE CHECK: Prevents new routes from pointing to the Core Kernel (Monolith).
    Strangler Fig Pattern: New functionality must be in Microservices.

    This test parses the API Gateway source code to ensure that no *new* functions
    reference `CORE_KERNEL_URL`. This enforces the "Stop the Bleeding" policy.
    """
    assert os.path.exists(GATEWAY_FILE), f"Gateway file not found: {GATEWAY_FILE}"

    with open(GATEWAY_FILE, "r") as f:
        tree = ast.parse(f.read())

    violations = []

    for node in ast.walk(tree):
        # We look for async functions (handlers)
        if isinstance(node, ast.AsyncFunctionDef):
            func_name = node.name

            # Check if function body references "CORE_KERNEL_URL" attribute
            # This is a heuristic: looking for usage of the constant name.
            references_core = False
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute):
                    if child.attr == "CORE_KERNEL_URL":
                        references_core = True
                        break

            if references_core:
                if func_name not in LEGACY_ALLOWLIST:
                    violations.append(func_name)

    if violations:
        error_msg = (
            f"\n\n[GOVERNANCE VIOLATION] The following new routes target the Monolith (Core Kernel):\n"
            f"{violations}\n\n"
            f"STOP! Do not add new routes to the Monolith. Create a Microservice instead.\n"
            f"Rule: The API Gateway must not expand its dependency on the Core Kernel.\n"
            f"Allowed Legacy Handlers: {sorted(list(LEGACY_ALLOWLIST))}\n"
        )
        raise AssertionError(error_msg)
