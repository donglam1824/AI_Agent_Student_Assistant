"""
services/multi_email_service.py
-------------------------------
Email service that combines Gmail and Outlook mailboxes.
"""

from __future__ import annotations

from typing import Optional

from config.settings import settings
from core.logger import logger
from models.email import EmailCreate, EmailMessage
from services.graph_email_service import BaseEmailService, GraphEmailService
from services.google_email_service import GoogleEmailService


class MultiEmailService(BaseEmailService):
    """Route email operations to Gmail, Outlook, or both."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._gmail: Optional[GoogleEmailService] = None
        self._outlook: Optional[GraphEmailService] = None

    @staticmethod
    def _normalize_source(source: Optional[str]) -> str:
        value = (source or "all").lower().strip()
        if value in {"google", "gmail"}:
            return "gmail"
        if value in {"msgraph", "microsoft", "outlook"}:
            return "outlook"
        if value in {"all", "multi", "both"}:
            return "all"
        return value

    @staticmethod
    def _prefix(source: str, email: EmailMessage) -> EmailMessage:
        raw_id = email.id
        if not raw_id.startswith(("gmail:", "outlook:")):
            raw_id = f"{source}:{raw_id}"
        return email.model_copy(update={"id": raw_id, "source": source})

    @staticmethod
    def _split_message_id(message_id: str, source: Optional[str] = None) -> tuple[str, str]:
        if ":" in message_id:
            prefix, raw_id = message_id.split(":", 1)
            return MultiEmailService._normalize_source(prefix), raw_id
        normalized = MultiEmailService._normalize_source(source)
        if normalized == "all":
            raise ValueError(
                "Can phai co prefix message_id dang gmail:<id> hoac outlook:<id> de tra loi email."
            )
        return normalized, message_id

    def _get_gmail(self) -> GoogleEmailService:
        if self._gmail is None:
            self._gmail = GoogleEmailService(user_id=self._user_id)
        return self._gmail

    def _get_outlook(self) -> GraphEmailService:
        if self._outlook is None:
            self._outlook = GraphEmailService(user_id=self._user_id)
        return self._outlook

    async def list_emails(self, limit: int = 50, source: Optional[str] = None) -> list[EmailMessage]:
        source_name = self._normalize_source(source)
        emails: list[EmailMessage] = []

        if source_name in {"all", "gmail"}:
            try:
                gmail_emails = await self._get_gmail().list_emails(limit=limit)
                emails.extend(self._prefix("gmail", email) for email in gmail_emails)
            except Exception as e:
                logger.error(f"[Multi Email] Gmail list failed: {e}")
                if source_name == "gmail":
                    raise

        if source_name in {"all", "outlook"}:
            try:
                outlook_emails = await self._get_outlook().list_emails(limit=limit)
                emails.extend(self._prefix("outlook", email) for email in outlook_emails)
            except Exception as e:
                logger.error(f"[Multi Email] Outlook list failed: {e}")
                if source_name == "outlook":
                    raise

        return emails[:limit] if source_name == "all" else emails

    async def send_email(self, data: EmailCreate) -> bool:
        source_name = self._normalize_source(data.source or settings.default_email_provider)
        if source_name == "gmail":
            return await self._get_gmail().send_email(data)
        if source_name == "outlook":
            return await self._get_outlook().send_email(data)
        raise ValueError("Khi gui email, source phai la 'gmail' hoac 'outlook'.")

    async def reply_email(self, message_id: str, body: str) -> bool:
        source_name, raw_id = self._split_message_id(message_id)
        if source_name == "gmail":
            return await self._get_gmail().reply_email(raw_id, body)
        if source_name == "outlook":
            return await self._get_outlook().reply_email(raw_id, body)
        raise ValueError("message_id phai co prefix gmail: hoac outlook:.")
