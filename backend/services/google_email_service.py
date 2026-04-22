"""
services/google_email_service.py
---------------------------------
Google Email (Gmail API) implementation.
"""

from __future__ import annotations
import os
import base64
from email.message import EmailMessage as PythonEmailMessage
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.email import EmailMessage, EmailCreate
from services.graph_email_service import BaseEmailService
from core.logger import logger

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def _get_credentials(credentials_path: str, token_path: str) -> Credentials:
    creds: Credentials | None = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("[Google Email] Refreshing expired token...")
            creds.refresh(Request())
        else:
            logger.info("[Google Email] No valid token. Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            try:
                creds = flow.run_local_server(port=0, timeout_seconds=15)
            except Exception as e:
                logger.warning(f"[Google Email] Local server failed ({e}). Falling back to manual auth.")
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                auth_url, _ = flow.authorization_url(prompt='consent')
                print("\n" + "="*60)
                print("⚠️ GMAIL AUTH: KHÔNG THỂ TỰ ĐỘNG BẮT MÃ XÁC THỰC ⚠️")
                print("1. Hãy mở đường link sau trong trình duyệt:")
                print(auth_url)
                code = input("\n2. Nhập mã code bạn nhận được từ Google: ").strip()
                print("="*60 + "\n")
                flow.fetch_token(code=code)
                creds = flow.credentials

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"[Google Email] Token saved to {token_path}")
    return creds


class GoogleEmailService(BaseEmailService):
    def __init__(self) -> None:
        from config.settings import settings
        creds = _get_credentials(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_email_path,
        )
        self._service = build("gmail", "v1", credentials=creds)
        logger.info("[Google Email] Gmail service ready.")

    async def list_emails(self, limit: int = 5) -> List[EmailMessage]:
        logger.info(f"[Google Email] Fetching {limit} emails")
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
                    received_date_time=date_str
                ))
            return email_list
        except HttpError as error:
            logger.error(f"[Google Email] list_emails error: {error}")
            raise

    async def send_email(self, data: EmailCreate) -> bool:
        logger.info(f"[Google Email] Sending email: {data.subject}")
        message = PythonEmailMessage()
        message.set_content(data.body)
        message['To'] = ", ".join(data.to_recipients)
        message['Subject'] = data.subject
        if data.cc_recipients:
            message['Cc'] = ", ".join(data.cc_recipients)
            
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }
        
        try:
            sent_message = self._service.users().messages().send(userId='me', body=create_message).execute()
            logger.info(f"[Google Email] Email sent, Message Id: {sent_message.get('id')}")
            return True
        except HttpError as error:
            logger.error(f"[Google Email] send_email error: {error}")
            return False
