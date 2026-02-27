# app/overmind/__init__.py
# ======================================================================================
# ==                             THE OVERMIND SYSTEM CORE                             ==
# ======================================================================================
#
# ⚔ PURPOSE (القصد):
#   This file establishes the `overmind` package and serves as its primary public
#   interface. It exposes the key components and services from the sub-packages,
#   providing a clean, unified entry point for the rest of the application.
#
#   By importing from here (e.g., `from microservices.orchestrator_service.src.services.overmind import orchestrator`), other parts
#   of the system do not need to know the internal structure of the Overmind package,
#   making our architecture more modular and easier to refactor in the future.
#
# 🧬 EXPORTS (الصادرات):
#   - orchestrator: The main service for running missions.
#   - schemas: Core Pydantic schemas for tasks and plans.
#
# ===============================================================================

# from . import orchestrator
# from . import schemas

__all__ = [
    # "orchestrator",
    # "schemas",
]
