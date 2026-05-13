"""
services/graph_email_service.py
---------------------------------
Abstraction over Email API.
"""

from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import requests

from models.email import EmailMessage, EmailCreate
from core.logger import logger


class BaseEmailService(ABC):
    @abstractmethod
    async def list_emails(self, limit: int = 5, source: Optional[str] = None) -> List[EmailMessage]: ...

    @abstractmethod
    async def send_email(self, data: EmailCreate) -> bool: ...

    @abstractmethod
    async def reply_email(self, message_id: str, body: str) -> bool: ...


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

    async def list_emails(self, limit: int = 5, source: Optional[str] = None) -> List[EmailMessage]:
        _ = source
        logger.debug(f"[Mock Email] Listing emails: limit={limit}")
        return self._store[:limit]

    async def send_email(self, data: EmailCreate) -> bool:
        logger.info(f"[Mock Email] Sent email '{data.subject}' to {data.to_recipients}")
        return True

    async def reply_email(self, message_id: str, body: str) -> bool:
        logger.info(f"[Mock Email] Replied to '{message_id}': {body[:80]}")
        return True


class GraphEmailService(BaseEmailService):
    """Real implementation using Microsoft Graph SDK."""
    def __init__(self, user_id: str | None = None) -> None:
        from core.auth import get_graph_client
        from config.settings import settings
        self._app_client = get_graph_client()
        self._local_user_id = user_id
        self._user_id = settings.graph_user_id

    def _delegated_token(self) -> str | None:
        if not self._local_user_id:
            return None
        from db.database import SessionLocal
        from services.microsoft_oauth_service import get_user_microsoft_access_token

        db = SessionLocal()
        try:
            return get_user_microsoft_access_token(db, self._local_user_id)
        except Exception as e:
            logger.warning(f"[Graph Email] Delegated token unavailable for user={self._local_user_id}: {e}")
            return None
        finally:
            db.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        token = self._delegated_token()
        if not token:
            raise ValueError("Microsoft account is not connected for this user.")
        response = requests.request(
            method,
            f"https://graph.microsoft.com/v1.0{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
            **kwargs,
        )
        if response.status_code >= 400:
            logger.error(f"[Graph Email] {method} {path} failed: {response.status_code} {response.text}")
            response.raise_for_status()
        return response

    async def list_emails(self, limit: int = 5, source: Optional[str] = None) -> List[EmailMessage]:
        _ = source
        if self._local_user_id:
            logger.info(f"[Graph Email] Fetching {limit} delegated emails")
            data = self._request("GET", "/me/messages", params={"$top": limit}).json()
            return [
                EmailMessage(
                    id=item.get("id", ""),
                    subject=item.get("subject") or "(Khong co tieu de)",
                    body_preview=item.get("bodyPreview") or "",
                    sender=((item.get("sender") or {}).get("emailAddress") or {}).get("address") or "unknown",
                    received_date_time=item.get("receivedDateTime") or "",
                    source="outlook",
                )
                for item in data.get("value", [])
            ]

        logger.info(f"[Graph Email] Fetching {limit} emails")
        result = await (
            self._app_client.users
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
                    received_date_time=m.received_date_time.isoformat() if m.received_date_time else "",
                    source="outlook",
                ))
        return emails

    async def send_email(self, data: EmailCreate) -> bool:
        if self._local_user_id:
            message = {
                "subject": data.subject,
                "body": {"contentType": "Text", "content": data.body},
                "toRecipients": [
                    {"emailAddress": {"address": address}} for address in data.to_recipients
                ],
            }
            if data.cc_recipients:
                message["ccRecipients"] = [
                    {"emailAddress": {"address": address}} for address in data.cc_recipients
                ]
            self._request("POST", "/me/sendMail", json={"message": message, "saveToSentItems": True})
            logger.info(f"[Graph Email] Sent delegated email '{data.subject}'")
            return True

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
        await self._app_client.users.by_user_id(self._user_id).send_mail.post(request_body)
        logger.info(f"[Graph Email] Sent email '{data.subject}'")
        return True

    async def reply_email(self, message_id: str, body: str) -> bool:
        from core.auth import get_graph_access_token

        if self._local_user_id:
            self._request("POST", f"/me/messages/{message_id}/reply", json={"comment": body})
            logger.info(f"[Graph Email] Replied to delegated message={message_id}")
            return True

        url = f"https://graph.microsoft.com/v1.0/users/{self._user_id}/messages/{message_id}/reply"
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {get_graph_access_token()}",
                "Content-Type": "application/json",
            },
            json={"comment": body},
            timeout=30,
        )
        if response.status_code >= 400:
            logger.error(f"[Graph Email] Reply failed: {response.status_code} {response.text}")
            response.raise_for_status()
        logger.info(f"[Graph Email] Replied to message={message_id}")
        return True


def get_email_service(user_id: str | None = None) -> BaseEmailService:
    from config.settings import settings
    provider = settings.email_provider.lower().strip()
    providers = [p.strip().lower() for p in settings.email_providers.split(",") if p.strip()]

    if provider == "mock" or settings.mock_graph:
        return MockEmailService()

    if provider in {"multi", "all"} or len(providers) > 1:
        from services.multi_email_service import MultiEmailService
        if not user_id:
            raise ValueError("MultiEmailService requires user_id")
        return MultiEmailService(user_id=user_id)

    if provider == "google":
        from services.google_email_service import GoogleEmailService
        if not user_id:
            raise ValueError("GoogleEmailService requires user_id")
        return GoogleEmailService(user_id=user_id)

    if provider in {"msgraph", "outlook"}:
        return GraphEmailService(user_id=user_id)

    raise ValueError(f"Unknown EMAIL_PROVIDER={provider!r}")
