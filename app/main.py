"""
نقطة الدخول الرئيسية لتطبيق CogniForge (Main Entry Point).

تم التبسيط بشكل جذري لتكون نقطة انطلاق خالية من المنطق (Logic-Free Bootstrapper).
المسؤولية الكاملة للتكوين والتهيئة تقع الآن على عاتق `RealityKernel`.

المبادئ:
- Separation of Concerns: ملف main.py فقط للتشغيل.
- Singleton Pattern: يتم الحصول على النواة عبر الكائن النهائي.
"""

import asyncio
import contextlib

from fastapi import FastAPI

from app.core.config import AppSettings, get_settings
from app.core.database import async_session_factory
from app.core.outbox import run_outbox_worker
from app.kernel import RealityKernel
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.static_files_middleware import StaticFilesConfig, setup_static_files_middleware

# 1. تهيئة الإعدادات
settings = get_settings()

# 2. بدء تشغيل النواة (Boot The Kernel)
_kernel = RealityKernel(settings=settings, enable_static_files=settings.ENABLE_STATIC_FILES)

# 3. تصدير كائن التطبيق (ASGI Interface)
app = _kernel.get_app()

# 4. تسجيل الميدل وير (Idempotency)
app.add_middleware(IdempotencyMiddleware)

# 5. تشغيل العامل في الخلفية (Outbox Worker)
_worker_task = None

@app.on_event("startup")
async def start_background_workers():
    """Start background workers for the application."""
    global _worker_task
    _worker_task = asyncio.create_task(run_outbox_worker(session_factory=async_session_factory))

@app.on_event("shutdown")
async def stop_background_workers():
    """Stop background workers gracefully."""
    # We only read the global here, so 'global _worker_task' declaration is technically redundant for reading,
    # but good for clarity. However, Ruff PLW0602 complains if we declare global but don't assign.
    # Since we only read it, we can remove the global declaration here.
    if _worker_task:
        _worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _worker_task

def create_app(
    *,
    settings_override: "AppSettings | None" = None,
    static_dir: str | None = None,
    enable_static_files: bool | None = None,
) -> FastAPI:
    """
    مصنع تطبيق مرن يسمح بالتهيئة حسب الحاجة دون تعديل الحالة العالمية.

    الأهداف:
    - دعم تمارين الاختبار التي تحتاج لمسارات ثابتة مخصصة.
    - احترام مبدأ التركيب الوظيفي عبر بناء النواة ثم إضافة واجهة الملفات الثابتة اختيارياً.
    """

    effective_settings = settings_override or get_settings()
    resolved_static = (
        effective_settings.ENABLE_STATIC_FILES
        if enable_static_files is None
        else enable_static_files
    )
    delegate_static = resolved_static and static_dir is None
    kernel = RealityKernel(settings=effective_settings, enable_static_files=delegate_static)
    application = kernel.get_app()

    # Register Middleware
    application.add_middleware(IdempotencyMiddleware)

    if resolved_static and not delegate_static:
        static_config = StaticFilesConfig(static_dir=static_dir)
        setup_static_files_middleware(application, static_config)

    return application
