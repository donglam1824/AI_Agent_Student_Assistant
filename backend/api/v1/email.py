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
    source: Optional[str] = None


class SendEmailRequest(BaseModel):
    subject: str
    body: str
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    source: Optional[str] = None


class ReplyEmailRequest(BaseModel):
    message_id: str
    body: str


class EmailSummaryResponse(BaseModel):
    id: str
    gmail_id: str
    subject: Optional[str]
    sender: Optional[str]
    received_at: Optional[str]
    scan_session: Optional[str]
    summary: Optional[str]
    priority: Optional[str]
    deadline: Optional[str]
    calendar_event_id: Optional[str]
    requires_reply: bool
    is_read: bool

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/inbox", response_model=list[EmailItem])
async def get_inbox(
    limit: int = 50,
    source: str = "all",
    current_user: User = Depends(get_current_user),
):
    """Get recent emails from Gmail inbox."""
    try:
        from services.graph_email_service import get_email_service
        service = get_email_service(user_id=current_user.id)
        emails = await service.list_emails(limit=limit, source=source)

        return [
            EmailItem(
                id=e.id,
                subject=e.subject,
                sender=e.sender,
                body_preview=e.body_preview,
                received_date_time=e.received_date_time,
                source=e.source,
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
        from services.graph_email_service import get_email_service
        from models.email import EmailCreate
        service = get_email_service(user_id=current_user.id)

        data = EmailCreate(
            subject=body.subject,
            body=body.body,
            to_recipients=body.to_recipients,
            cc_recipients=body.cc_recipients,
            source=body.source,
        )
        success = await service.send_email(data)

        if success:
            return {"message": f"Đã gửi email '{body.subject}' thành công."}
        raise HTTPException(status_code=500, detail="Gửi email thất bại.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi email: {str(e)}")


@router.post("/reply")
async def reply_email(
    body: ReplyEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """Reply to a Gmail or Outlook message."""
    try:
        from services.graph_email_service import get_email_service

        service = get_email_service(user_id=current_user.id)
        success = await service.reply_email(message_id=body.message_id, body=body.body)

        if success:
            return {"message": f"Da tra loi email {body.message_id}."}
        raise HTTPException(status_code=500, detail="Tra loi email that bai.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email reply error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi tra loi email: {str(e)}")


@router.get("/summaries", response_model=list[EmailSummaryResponse])
async def get_summaries(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summarized emails from the database."""
    try:
        from db.crud import get_email_summaries
        summaries = get_email_summaries(db, user_id=current_user.id, limit=limit)
        
        # Convert datetime to ISO string for JSON serialization
        results = []
        for s in summaries:
            s_dict = {
                "id": s.id,
                "gmail_id": s.gmail_id,
                "subject": s.subject,
                "sender": s.sender,
                "received_at": s.received_at.isoformat() if s.received_at else None,
                "scan_session": s.scan_session,
                "summary": s.summary,
                "priority": s.priority,
                "deadline": s.deadline.isoformat() if s.deadline else None,
                "calendar_event_id": s.calendar_event_id,
                "requires_reply": s.requires_reply,
                "is_read": s.is_read
            }
            results.append(s_dict)
            
        return results
    except Exception as e:
        logger.error(f"Email summaries fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy tóm tắt email: {str(e)}")
