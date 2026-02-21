"""
Boundaries Services Module - Service Boundary Implementations
==============================================================

This module provides boundary service implementations that act as facades
for various domain operations, following Clean Architecture principles.

يوفر هذا الوحدة خدمات الحدود التي تعمل كواجهات موحدة لعمليات النطاق المختلفة،
متبعةً مبادئ البنية النظيفة (Clean Architecture).

Module Structure:
- admin_chat_boundary_service: Admin chat operations facade
- auth_boundary_service: Authentication operations facade
- customer_chat_boundary_service: Customer chat operations facade
- observability_boundary_service: Observability operations facade

Standards Applied:
- CS50 2025: Professional Arabic documentation, type strictness
- SOLID: Separation of Concerns, Single Responsibility
- Clean Architecture: Boundary pattern for layer isolation
"""

from app.services.boundaries.admin_chat_boundary_service import AdminChatBoundaryService
from app.services.boundaries.customer_chat_boundary_service import CustomerChatBoundaryService
from app.services.boundaries.observability_boundary_service import ObservabilityBoundaryService

__all__ = [
    "AdminChatBoundaryService",
    "CustomerChatBoundaryService",
    "ObservabilityBoundaryService",
]
