"""
واجهة برمجة تطبيقات محادثة العملاء القياسيين.

توفر نقاط النهاية الخاصة بالمستخدمين القياسيين للوصول إلى محادثة تعليمية
مع فرض سياسات الأمان والملكية.
"""

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.customer_chat import CustomerConversationDetails, CustomerConversationSummary
from app.api.routers.ws_auth import extract_websocket_auth
from app.core.database import async_session_factory, get_db
from app.core.di import get_logger
from app.core.domain.user import User
from app.deps.auth import CurrentUser, require_permissions
from app.services.boundaries.customer_chat_boundary_service import CustomerChatBoundaryService
from app.services.auth.token_decoder import decode_user_id
from app.services.chat.websocket_authority import ChatWebSocketPolicy, stream_chat_via_orchestrator
from app.services.rbac import QA_SUBMIT

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/chat",
    tags=["Customer Chat"],
)


def get_session_factory() -> Callable[[], AsyncSession]:
    """تبعية لاسترجاع مصنع الجلسات."""
    return async_session_factory


def get_chat_actor(
    current: CurrentUser = Depends(require_permissions(QA_SUBMIT)),
) -> CurrentUser:
    """تبعية تضمن امتلاك صلاحية الأسئلة التعليمية."""
    return current


def get_current_user_id(current: CurrentUser = Depends(get_chat_actor)) -> int:
    """إرجاع معرف المستخدم الحالي بعد تحقق الصلاحيات."""
    return current.user.id


async def get_actor_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    جلب كائن المستخدم الفعلي بعد التحقق من الحالة.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")
    await db.refresh(user)
    db.expunge(user)
    return user


def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerChatBoundaryService:
    """تبعية للحصول على خدمة حدود محادثة العملاء."""
    return CustomerChatBoundaryService(db)


@router.websocket("/ws")
async def chat_stream_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    قناة WebSocket لبث محادثة تعليمية للمستخدم القياسي.
    """
    await stream_chat_via_orchestrator(
        websocket=websocket,
        db=db,
        policy=ChatWebSocketPolicy(
            requires_admin=False,
            forbidden_details="Admin accounts must use the admin chat endpoint.",
            route_id="chat_ws_customer",
        ),
        auth_extractor=extract_websocket_auth,
        user_decoder=decode_user_id,
    )


@router.get(
    "/latest",
    summary="استرجاع آخر محادثة",
    response_model=CustomerConversationDetails | None,
)
async def get_latest_chat(
    actor: User = Depends(get_actor_user),
    service: CustomerChatBoundaryService = Depends(get_customer_service),
) -> CustomerConversationDetails | None:
    conversation_data = await service.get_latest_conversation_details(actor)
    if not conversation_data:
        return None
    return CustomerConversationDetails.model_validate(conversation_data)


@router.get(
    "/conversations",
    summary="سرد المحادثات",
    response_model=list[CustomerConversationSummary],
)
async def list_conversations(
    actor: User = Depends(get_actor_user),
    service: CustomerChatBoundaryService = Depends(get_customer_service),
) -> list[CustomerConversationSummary]:
    results = await service.list_user_conversations(actor)
    return [CustomerConversationSummary.model_validate(r) for r in results]


@router.get(
    "/conversations/{conversation_id}",
    summary="تفاصيل محادثة",
    response_model=CustomerConversationDetails,
    description="استرجاع تفاصيل محادثة محددة.",
    operation_id="chatConversationGet",
)
async def get_conversation(
    conversation_id: int,
    actor: User = Depends(get_actor_user),
    service: CustomerChatBoundaryService = Depends(get_customer_service),
) -> CustomerConversationDetails:
    data = await service.get_conversation_details(actor, conversation_id)
    return CustomerConversationDetails.model_validate(data)
