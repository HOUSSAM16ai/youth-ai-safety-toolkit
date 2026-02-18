"""
واجهة عميل النماذج اللغوية (ISP).
---------------------------------
تحدد العقد لأي مزود لنموذج لغوي كبير.
"""

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from microservices.orchestrator_service.src.core.types import JSONDict


@runtime_checkable
class LLMClient(Protocol):
    """
    بروتوكول يعرّف واجهة عملاء الذكاء الاصطناعي.
    يلتزم بمبدأ ISP عبر إبقاء الطرق الأساسية فقط للتفاعل.
    """

    async def stream_chat(self, messages: list[JSONDict]) -> AsyncGenerator[JSONDict, None]:
        """بث محادثة دردشة على شكل دفعات."""
        ...

    async def send_message(
        self, system_prompt: str, user_message: str, temperature: float = 0.7
    ) -> str:
        """إرسال رسالة واحدة وإرجاع النص الكامل للاستجابة."""
        ...

    # Legacy support (can be deprecated later)
    async def generate_text(self, prompt: str, **kwargs) -> object:
        """مساعد لتوليد النص مع الحفاظ على التوافق الخلفي."""
        ...

    async def forge_new_code(self, **kwargs) -> object:
        """مساعد لتوليد الشيفرة مع الحفاظ على التوافق الخلفي."""
        ...
