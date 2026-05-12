"""
services/google_email_service.py
---------------------------------
Google Email (Gmail API) implementation – multi-tenant, token từ Database.
"""

from __future__ import annotations
import base64
from email.message import EmailMessage as PythonEmailMessage
from typing import List, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.email import EmailMessage, EmailCreate
from services.graph_email_service import BaseEmailService
from core.logger import logger

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _get_credentials_from_db(user_id: str) -> Credentials:
    """Truy vấn DB lấy token đã mã hóa, giải mã và tạo Credentials cho Gmail."""
    from db.database import SessionLocal
    from db import crud
    from core.crypto import decrypt_token
    from config.settings import settings

    db = SessionLocal()
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise ValueError(f"User {user_id} không tồn tại trong DB.")

        access_token = decrypt_token(user.google_access_token)
        refresh_token = decrypt_token(user.google_refresh_token)

        if not access_token and not refresh_token:
            raise ValueError(
                f"User {user_id} chưa có Google token. Vui lòng đăng nhập lại."
            )

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
        )

        if not creds.valid and creds.refresh_token:
            logger.info(f"[Google Email] Refreshing token for user={user_id}")
            creds.refresh(Request())
            crud.update_user_tokens(
                db=db,
                user_id=user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
            )

        return creds
    finally:
        db.close()


class GoogleEmailService(BaseEmailService):
    def __init__(self, user_id: str) -> None:
        creds = _get_credentials_from_db(user_id)
        self._service = build("gmail", "v1", credentials=creds)
        self._user_id = user_id
        logger.info(f"[Google Email] Gmail service ready for user={user_id}")

    async def list_emails(self, limit: int = 5, source: Optional[str] = None) -> List[EmailMessage]:
        _ = source
        logger.info(f"[Google Email] user={self._user_id} fetching {limit} emails")
        try:
            results = self._service.users().messages().list(userId='me', maxResults=limit).execute()
            messages = results.get('messages', [])
            email_list = []

            for msg in messages:
                msg_data = self._service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
                headers = msg_data.get('payload', {}).get('headers', [])

                subject = "(Không có tiêu đề)"
                sender = "unknown"
                date_str = ""

                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    if header['name'].lower() == 'from':
                        sender = header['value']
                    if header['name'].lower() == 'date':
                        date_str = header['value']

                email_list.append(EmailMessage(
                    id=msg['id'],
                    subject=subject,
                    body_preview=msg_data.get('snippet', ''),
                    sender=sender,
                    received_date_time=date_str,
                    source="gmail",
                ))
            return email_list
        except HttpError as error:
            logger.error(f"[Google Email] list_emails error: {error}")
            raise

    async def get_emails_since(self, timestamp: datetime, limit: int = 50) -> List[dict]:
        """Fetch emails received after the given timestamp. Returns dict with full details for analysis."""
        logger.info(f"[Google Email] user={self._user_id} fetching emails since {timestamp}")
        try:
            query = f"after:{int(timestamp.timestamp())}"
            results = self._service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
            messages = results.get('messages', [])
            email_list = []

            for msg in messages:
                # Need full format for LLM to extract deadline from body
                msg_data = self._service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = msg_data.get('payload', {}).get('headers', [])

                subject = "(Không có tiêu đề)"
                sender = "unknown"
                date_str = ""

                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    if header['name'].lower() == 'from':
                        sender = header['value']
                    if header['name'].lower() == 'date':
                        date_str = header['value']

                # Extract body
                body = ""
                payload = msg_data.get('payload', {})
                
                def get_body(part):
                    body_text = ""
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data')
                        if data:
                            body_text = base64.urlsafe_b64decode(data).decode('utf-8')
                    elif 'parts' in part:
                        for p in part['parts']:
                            body_text += get_body(p)
                    return body_text
                
                body = get_body(payload)
                if not body and payload.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

                email_list.append({
                    "id": msg['id'],
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "snippet": msg_data.get('snippet', ''),
                    "body": body
                })
            return email_list
        except HttpError as error:
            logger.error(f"[Google Email] get_emails_since error: {error}")
            raise


    async def send_email(self, data: EmailCreate) -> bool:
        logger.info(f"[Google Email] user={self._user_id} sending: {data.subject}")
        message = PythonEmailMessage()
        message.set_content(data.body)
        message['To'] = ", ".join(data.to_recipients)
        message['Subject'] = data.subject
        if data.cc_recipients:
            message['Cc'] = ", ".join(data.cc_recipients)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            sent = self._service.users().messages().send(userId='me', body={'raw': encoded_message}).execute()
            logger.info(f"[Google Email] Email sent, id={sent.get('id')}")
            return True
        except HttpError as error:
            logger.error(f"[Google Email] send_email error: {error}")
            return False

    async def reply_email(self, message_id: str, body: str) -> bool:
        logger.info(f"[Google Email] user={self._user_id} replying to: {message_id}")
        try:
            original = self._service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Message-ID', 'References'],
            ).execute()
            headers = original.get('payload', {}).get('headers', [])
            header_map = {h.get('name', '').lower(): h.get('value', '') for h in headers}

            subject = header_map.get('subject') or "(Khong co tieu de)"
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"

            sender = header_map.get('from')
            message = PythonEmailMessage()
            message.set_content(body)
            message['To'] = sender
            message['Subject'] = subject

            message_id_header = header_map.get('message-id')
            references = header_map.get('references')
            if message_id_header:
                message['In-Reply-To'] = message_id_header
                message['References'] = f"{references} {message_id_header}".strip()

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self._service.users().messages().send(
                userId='me',
                body={
                    'raw': encoded_message,
                    'threadId': original.get('threadId'),
                },
            ).execute()
            logger.info(f"[Google Email] Replied to message={message_id}")
            return True
        except HttpError as error:
            logger.error(f"[Google Email] reply_email error: {error}")
            return False
