"""
services/graph_email_service.py
---------------------------------
Abstraction over Email API.
"""

from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import List

from models.email import EmailMessage, EmailCreate
from core.logger import logger


class BaseEmailService(ABC):
    @abstractmethod
    async def list_emails(self, limit: int = 5) -> List[EmailMessage]: ...

    @abstractmethod
    async def send_email(self, data: EmailCreate) -> bool: ...


class MockEmailService(BaseEmailService):
    def __init__(self) -> None:
        self._store: list[EmailMessage] = []
        self._seed()

    def _seed(self) -> None:
        self._store.append(
            EmailMessage(
                id=str(uuid.uuid4()),
                subject="Chào mừng đến với lớp học",
                body_preview="Thông tin đăng nhập của bạn là...",
                sender="giangvien@truong.edu.vn",
                received_date_time="2026-03-26T10:00:00Z"
            )
        )

    async def list_emails(self, limit: int = 5) -> List[EmailMessage]:
        logger.debug(f"[Mock Email] Listing emails: limit={limit}")
        return self._store[:limit]

    async def send_email(self, data: EmailCreate) -> bool:
        logger.info(f"[Mock Email] Sent email '{data.subject}' to {data.to_recipients}")
        return True


class GraphEmailService(BaseEmailService):
    """Real implementation using Microsoft Graph SDK."""
    def __init__(self) -> None:
        from core.auth import get_graph_client
        from config.settings import settings
        self._client = get_graph_client()
        self._user_id = settings.graph_user_id

    async def list_emails(self, limit: int = 5) -> List[EmailMessage]:
        logger.info(f"[Graph Email] Fetching {limit} emails")
        result = await (
            self._client.users
            .by_user_id(self._user_id)
            .messages
            .get(request_configuration=lambda cfg: setattr(
                cfg.query_parameters, "top", limit
            ))
        )
        emails = []
        if result and result.value:
            for m in result.value:
                emails.append(EmailMessage(
                    id=m.id or "",
                    subject=m.subject or "(Không có tiêu đề)",
                    body_preview=m.body_preview or "",
                    sender=m.sender.email_address.address if m.sender and m.sender.email_address else "unknown",
                    received_date_time=m.received_date_time.isoformat() if m.received_date_time else ""
                ))
        return emails

    async def send_email(self, data: EmailCreate) -> bool:
        from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
        from msgraph.generated.models.message import Message
        from msgraph.generated.models.item_body import ItemBody
        from msgraph.generated.models.body_type import BodyType
        from msgraph.generated.models.recipient import Recipient
        from msgraph.generated.models.email_address import EmailAddress

        message = Message()
        message.subject = data.subject
        message.body = ItemBody(content=data.body, content_type=BodyType.Text)
        message.to_recipients = [
            Recipient(email_address=EmailAddress(address=r)) for r in data.to_recipients
        ]
        if data.cc_recipients:
            message.cc_recipients = [
                Recipient(email_address=EmailAddress(address=r)) for r in data.cc_recipients
            ]

        request_body = SendMailPostRequestBody(message=message, save_to_sent_items=True)
        await self._client.users.by_user_id(self._user_id).send_mail.post(request_body)
        logger.info(f"[Graph Email] Sent email '{data.subject}'")
        return True


def get_email_service() -> BaseEmailService:
    from config.settings import settings
    provider = settings.email_provider.lower().strip()

    if provider == "mock" or settings.mock_graph:
        return MockEmailService()

    if provider == "google":
        from services.google_email_service import GoogleEmailService
        return GoogleEmailService()

    if provider == "msgraph":
        return GraphEmailService()

    raise ValueError(f"Unknown EMAIL_PROVIDER={provider!r}")
