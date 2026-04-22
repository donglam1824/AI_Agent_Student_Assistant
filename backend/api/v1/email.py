"""
api/v1/email.py
---------------
Email proxy endpoints:
  - GET  /email/inbox  → List recent emails from Gmail
  - POST /email/send   → Send an email via Gmail
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/email", tags=["Email"])


# ── Request / Response Models ─────────────────────────────────────────────

class EmailItem(BaseModel):
    id: str
    subject: str
    sender: str
    body_preview: str
    received_date_time: str


class SendEmailRequest(BaseModel):
    subject: str
    body: str
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/inbox", response_model=list[EmailItem])
async def get_inbox(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    """Get recent emails from Gmail inbox."""
    try:
        from services.google_email_service import GoogleEmailService
        service = GoogleEmailService()
        import asyncio
        emails = asyncio.run(service.list_emails(limit=limit))

        return [
            EmailItem(
                id=e.id,
                subject=e.subject,
                sender=e.sender,
                body_preview=e.body_preview,
                received_date_time=e.received_date_time,
            )
            for e in emails
        ]
    except Exception as e:
        logger.error(f"Email inbox error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy email: {str(e)}")


@router.post("/send")
async def send_email(
    body: SendEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """Send an email via Gmail."""
    try:
        from services.google_email_service import GoogleEmailService
        from models.email import EmailCreate
        service = GoogleEmailService()

        data = EmailCreate(
            subject=body.subject,
            body=body.body,
            to_recipients=body.to_recipients,
            cc_recipients=body.cc_recipients,
        )
        import asyncio
        success = asyncio.run(service.send_email(data))

        if success:
            return {"message": f"Đã gửi email '{body.subject}' thành công."}
        raise HTTPException(status_code=500, detail="Gửi email thất bại.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi email: {str(e)}")
