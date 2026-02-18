"""
نظام المعرفة الذاتية لـ Overmind (Self-Knowledge System).

هذا النظام يوفر لـ Overmind معرفة كاملة عن نفسه وعن المشروع:
- من المؤسس؟
- ما هي الفلسفة والمبادئ؟
- تاريخ التطور
- الإصدارات والتحديثات
- القدرات والميزات

المبادئ المطبقة:
- Self-Awareness: النظام يعرف نفسه
- Documentation as Code: المعرفة مُدمجة في الكود
- Single Source of Truth: مصدر واحد للحقيقة
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.agents.principles import get_agent_principles
from microservices.orchestrator_service.src.services.overmind.agents.system_principles import (
    format_architecture_system_principles,
    format_system_principles,
    get_architecture_system_principles,
    get_system_principles,
)
from microservices.orchestrator_service.src.services.overmind.dec_pomdp_proof import (
    build_dec_pomdp_proof_summary,
    format_dec_pomdp_proof_summary,
    is_dec_pomdp_proof_question,
)
from microservices.orchestrator_service.src.services.overmind.domain.identity_models import (
    AgentPrinciple,
    IdentitySchema,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class _QuestionHandler:
    """يمثل قاعدة توجيه سؤال إلى إجابة محددة."""

    predicate: Callable[[str], bool]
    responder: Callable[[], str]


class OvermindIdentity:
    """
    هوية وشخصية Overmind (Overmind's Identity).

    تحتوي على جميع المعلومات الأساسية عن Overmind:
    - المؤسس والفريق
    - الفلسفة والرؤية
    - التاريخ والتطور
    - القدرات والإمكانيات

    الاستخدام:
        >>> identity = OvermindIdentity()
        >>> logger.info(identity.get_founder())
        "Houssam Benmerah"
        >>> logger.info(identity.answer_question("من هو مؤسس overmind"))
        "مؤسس Overmind هو Houssam Benmerah..."
    """

    def __init__(self) -> None:
        """تهيئة هوية Overmind."""
        self.identity_model = self._load_identity()

        self._question_handlers: list[_QuestionHandler] = [
            _QuestionHandler(self._is_founder_question, self._answer_founder_question),
            _QuestionHandler(self._is_overmind_question, self._answer_overmind_question),
            _QuestionHandler(
                self._is_agent_principles_question, self._answer_agent_principles_question
            ),
            _QuestionHandler(
                self._is_system_principles_question, self._answer_system_principles_question
            ),
            _QuestionHandler(
                self._is_architecture_principles_question,
                self._answer_architecture_principles_question,
            ),
            _QuestionHandler(self._is_agents_question, self._answer_agents_question),
            _QuestionHandler(self._is_capabilities_question, self._answer_capabilities_question),
            _QuestionHandler(self._is_project_question, self._answer_project_question),
            _QuestionHandler(self._is_philosophy_question, self._answer_philosophy_question),
            _QuestionHandler(self._is_birth_date_question, self._answer_birth_date_question),
            _QuestionHandler(self._is_history_question, self._answer_history_question),
            _QuestionHandler(self._is_dec_pomdp_question, self._answer_dec_pomdp_question),
        ]

    def _load_identity(self) -> IdentitySchema:
        """تحميل الهوية من ملف JSON ودمج المبادئ الديناميكية."""
        # Locate the JSON file relative to the package structure
        # Assuming app/services/overmind/data/identity.json
        base_path = Path(__file__).parent / "data" / "identity.json"

        if not base_path.exists():
            # Fallback or error, for now let's assume it exists or raise
            raise FileNotFoundError(f"Identity data not found at {base_path}")

        with open(base_path, encoding="utf-8") as f:
            data = json.load(f)

        # Create the schema (this validates the JSON part)
        schema = IdentitySchema(**data)

        # Inject dynamic principles
        schema.agent_principles = [
            AgentPrinciple(number=p.number, statement=p.statement) for p in get_agent_principles()
        ]
        schema.system_principles = [
            AgentPrinciple(number=p.number, statement=p.statement) for p in get_system_principles()
        ]
        schema.architecture_system_principles = [
            AgentPrinciple(number=p.number, statement=p.statement)
            for p in get_architecture_system_principles()
        ]

        return schema

    def get_founder(self) -> str:
        """
        الحصول على اسم المؤسس.

        Returns:
            str: اسم المؤسس
        """
        return self.identity_model.founder.name

    def get_founder_info(self) -> dict[str, object]:
        """
        الحصول على معلومات المؤسس الكاملة.

        Returns:
            dict: جميع معلومات المؤسس
        """
        return self.identity_model.founder.model_dump()

    def get_project_info(self) -> dict[str, object]:
        """
        الحصول على معلومات المشروع.

        Returns:
            dict: معلومات المشروع
        """
        return self.identity_model.project.model_dump()

    def get_overmind_info(self) -> dict[str, object]:
        """
        الحصول على معلومات Overmind.

        Returns:
            dict: معلومات Overmind
        """
        return self.identity_model.overmind.model_dump()

    def get_philosophy(self) -> dict[str, object]:
        """
        الحصول على الفلسفة والمبادئ.

        Returns:
            dict: الفلسفة والمبادئ
        """
        return self.identity_model.philosophy.model_dump()

    def get_agents_info(self) -> dict[str, object]:
        """
        الحصول على معلومات الوكلاء.

        Returns:
            dict: معلومات جميع الوكلاء
        """
        return {k: v.model_dump() for k, v in self.identity_model.agents.items()}

    def get_agent_principles(self) -> list[dict[str, int | str]]:
        """
        الحصول على مبادئ الوكلاء بشكل منظم.

        Returns:
            list: قائمة مبادئ الوكلاء مع الأرقام والنصوص.
        """
        return [p.model_dump() for p in self.identity_model.agent_principles]

    def get_system_principles(self) -> list[dict[str, int | str]]:
        """
        الحصول على مبادئ النظام الصارمة بشكل منظم.

        Returns:
            list: قائمة مبادئ النظام مع الأرقام والنصوص.
        """
        return [p.model_dump() for p in self.identity_model.system_principles]

    def get_architecture_system_principles(self) -> list[dict[str, int | str]]:
        """
        الحصول على مبادئ المعمارية وحوكمة البيانات بشكل منظم.

        Returns:
            list: قائمة مبادئ المعمارية مع الأرقام والنصوص.
        """
        return [p.model_dump() for p in self.identity_model.architecture_system_principles]

    def get_capabilities(self) -> dict[str, object]:
        """
        الحصول على القدرات والإمكانيات.

        Returns:
            dict: جميع القدرات
        """
        return self.identity_model.capabilities.model_dump()

    def answer_question(self, question: str) -> str:
        """
        الإجابة على سؤال عن Overmind أو المشروع.

        Args:
            question: السؤال المطروح

        Returns:
            str: الإجابة
        """
        q = question.lower()

        # التحقق من نوع السؤال وتوجيهه للـ handler المناسب
        for handler in self._question_handlers:
            if handler.predicate(q):
                return handler.responder()
        return self._answer_unknown_question()

    def _is_founder_question(self, q: str) -> bool:
        keywords = [
            "مؤسس",
            "founder",
            "creator",
            "من أنشأ",
            "من بنى",
            "who is the",
            "who founded",
            "who created",
        ]
        return any(keyword in q for keyword in keywords)

    def _is_overmind_question(self, q: str) -> bool:
        keywords = ["ما هو overmind", "what is overmind", "من أنت", "who are you"]
        return any(keyword in q for keyword in keywords)

    def _is_agents_question(self, q: str) -> bool:
        return any(keyword in q for keyword in ["وكلاء", "agents", "الفريق"])

    def _is_agent_principles_question(self, q: str) -> bool:
        keywords = [
            "مبادئ الوكلاء",
            "مبادئ الوكيل",
            "agent principles",
            "multi-agent",
            "multi agent",
        ]
        return any(keyword in q for keyword in keywords)

    def _is_system_principles_question(self, q: str) -> bool:
        keywords = [
            "المبادئ الصارمة",
            "المبادئ الصارمة للنظام",
            "system principles",
            "strict system principles",
        ]
        return any(keyword in q for keyword in keywords)

    def _is_architecture_principles_question(self, q: str) -> bool:
        keywords = [
            "مبادئ المعمارية",
            "المبادئ المعمارية",
            "حوكمة البيانات",
            "architecture principles",
            "data governance",
        ]
        return any(keyword in q for keyword in keywords)

    def _is_capabilities_question(self, q: str) -> bool:
        keywords = ["قدرات", "capabilities", "ماذا تستطيع", "what can you do"]
        return any(keyword in q for keyword in keywords)

    def _is_project_question(self, q: str) -> bool:
        return any(keyword in q for keyword in ["مشروع", "project", "cogniforge"])

    def _is_philosophy_question(self, q: str) -> bool:
        return any(keyword in q for keyword in ["فلسفة", "philosophy", "مبادئ", "principles"])

    def _is_birth_date_question(self, q: str) -> bool:
        return (
            "تاريخ ميلاد" in q
            or "birth date" in q
            or "متى ولد" in q
            or ("when was" in q and ("born" in q or "birthday" in q))
        )

    def _is_history_question(self, q: str) -> bool:
        return any(keyword in q for keyword in ["تاريخ", "history", "متى", "when"])

    def _is_dec_pomdp_question(self, q: str) -> bool:
        return is_dec_pomdp_proof_question(q)

    def _answer_founder_question(self) -> str:
        founder = self.identity_model.founder
        return (
            f"مؤسس Overmind هو {founder.name_ar} ({founder.name}). "
            f"الاسم: {founder.first_name_ar} ({founder.first_name}), "
            f"اللقب: {founder.last_name_ar} ({founder.last_name}). "
            f"تاريخ الميلاد: {founder.birth_date} (11 أغسطس 1997). "
            f"هو {founder.role_ar} ({founder.role}) للمشروع. "
            f"يمكنك التواصل معه عبر GitHub: @{founder.github}"
        )

    def _answer_overmind_question(self) -> str:
        overmind = self.identity_model.overmind
        return (
            f"أنا {overmind.name_ar} (Overmind)، {overmind.role_ar}. "
            f"مهمتي هي {overmind.purpose}. "
            f"تم إنشائي في {overmind.birth_date} وأنا حالياً في الإصدار {overmind.version}."
        )

    def _answer_agents_question(self) -> str:
        agents = self.identity_model.agents
        agents_list = [f"• {agent.name}: {agent.role}" for agent in agents.values()]
        return "أنا أعمل مع فريق من 4 وكلاء متخصصة:\n" + "\n".join(agents_list)

    def _answer_agent_principles_question(self) -> str:
        principles = self.identity_model.agent_principles
        formatted = "\n".join(f"{item.number}. {item.statement}" for item in principles)
        return "مبادئ الوكلاء المعتمدة لدينا هي:\n" + formatted

    def _answer_system_principles_question(self) -> str:
        return format_system_principles(
            header="المبادئ الصارمة للنظام هي:",
            bullet="",
            include_header=True,
        )

    def _answer_architecture_principles_question(self) -> str:
        return format_architecture_system_principles(
            header="مبادئ المعمارية وحوكمة البيانات الأساسية هي:",
            bullet="",
            include_header=True,
        )

    def _answer_capabilities_question(self) -> str:
        caps = self.identity_model.capabilities
        sections = [
            ("📚 المعرفة", caps.knowledge),
            ("⚡ الإجراءات", caps.actions),
            ("🧠 الذكاء", caps.intelligence),
            ("🛠️ الأدوات الخارقة (Super Tools)", caps.super_tools),
        ]

        response = "لدي قدرات واسعة وفائقة التطور:\n\n"
        response += "\n\n".join(
            f"{title}:\n" + "\n".join(f"• {item}" for item in items) for title, items in sections
        )
        return response

    def _answer_project_question(self) -> str:
        project = self.identity_model.project
        return (
            f"المشروع الذي أنتمي إليه هو {project.name}. "
            f"{project.description}. "
            f"يمكنك زيارة المستودع على: {project.repository}"
        )

    def _answer_philosophy_question(self) -> str:
        philosophy = self.identity_model.philosophy
        principles = "\n".join(f"• {p}" for p in philosophy.principles)
        return f"أتبع فلسفة {philosophy.heritage}. المبادئ الأساسية:\n{principles}"

    def _answer_birth_date_question(self) -> str:
        founder = self.identity_model.founder
        return (
            f"تاريخ ميلاد المؤسس {founder.name_ar} ({founder.name}) "
            f"هو {founder.birth_date} (11 أغسطس 1997 / August 11, 1997)."
        )

    def _answer_history_question(self) -> str:
        history = self.identity_model.history.milestones
        milestones = "\n".join(f"• {m.date}: {m.event}" for m in history)
        return f"أهم المعالم في تاريخي:\n{milestones}"

    def _answer_dec_pomdp_question(self) -> str:
        summary = build_dec_pomdp_proof_summary()
        return format_dec_pomdp_proof_summary(summary)

    def _answer_unknown_question(self) -> str:
        return (
            "عذراً، لم أفهم سؤالك تماماً. يمكنك سؤالي عن:\n"
            "• المؤسس (من مؤسس overmind؟)\n"
            "• نفسي (ما هو overmind؟)\n"
            "• الوكلاء (من هم الوكلاء؟)\n"
            "• المبادئ الصارمة للنظام (ما هي المبادئ الصارمة؟)\n"
            "• مبادئ المعمارية وحوكمة البيانات (ما هي مبادئ المعمارية؟)\n"
            "• القدرات (ماذا تستطيع أن تفعل؟)\n"
            "• المشروع (ما هو المشروع؟)\n"
            "• الفلسفة (ما هي الفلسفة؟)\n"
            "• التاريخ (ما هو تاريخك؟)"
        )

    def get_full_identity(self) -> dict[str, object]:
        """
        الحصول على الهوية الكاملة.

        Returns:
            dict: جميع معلومات الهوية
        """
        return self.identity_model.model_dump()
