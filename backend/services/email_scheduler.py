"""
backend/services/email_scheduler.py
-----------------------------------
Lập lịch chạy quét email định kỳ theo cấu hình (mặc định 4 buổi/ngày) 
bằng APScheduler.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
import pytz
from core.logger import logger
from db.database import SessionLocal
from db.models import User

# Khởi tạo scheduler
scheduler = BackgroundScheduler(timezone=pytz.utc)

SCAN_SCHEDULE = [
    {"hour": 7,  "minute": 30, "label": "morning"},
    {"hour": 12, "minute": 0,  "label": "noon"},
    {"hour": 17, "minute": 0,  "label": "afternoon"},
    {"hour": 21, "minute": 0,  "label": "evening"},
]

def scan_academic_emails(user_id: str, scan_session: str):
    """
    Job function để quét email cho một user tại một session cụ thể.
    """
    logger.info(f"Running scheduled email scan: user_id={user_id}, session={scan_session}")
    db = SessionLocal()
    try:
        from db.crud import get_email_preference
        pref = get_email_preference(db, user_id)
        last_scan = pref.last_scan_at if pref and pref.last_scan_at else None
        
        # Nếu chưa từng quét, lấy từ hôm qua
        if not last_scan:
            from datetime import timedelta
            last_scan = datetime.now(timezone.utc) - timedelta(days=1)
            
        from services.google_email_service import GoogleEmailService

        import asyncio
        email_svc = GoogleEmailService(user_id)
        emails = asyncio.run(email_svc.get_emails_since(last_scan, limit=20))
        
        if emails:
            # Lọc email học thuật bằng module dùng chung (đa tầng)
            from services.academic_filter import filter_academic_emails
            from models.email import EmailMessage

            # Chuyển dict → EmailMessage để dùng academic_filter
            email_messages = [
                EmailMessage(
                    id=e["id"],
                    subject=e.get("subject", ""),
                    body_preview=e.get("snippet", ""),
                    sender=e.get("sender", ""),
                    received_date_time=e.get("date", ""),
                    source="gmail",
                )
                for e in emails
            ]
            academic_msgs, _ = filter_academic_emails(email_messages, user_id=user_id)

            # Map lại về raw dict cho email_analyzer (cần body đầy đủ)
            academic_ids = {msg.id for msg in academic_msgs}
            filtered_emails = [e for e in emails if e["id"] in academic_ids]

            if filtered_emails:
                from services.email_analyzer import analyze_and_store_emails

                analyze_and_store_emails(user_id, filtered_emails, scan_session)
            
        # Cập nhật last_scan
        if pref:
            pref.last_scan_at = datetime.now(timezone.utc)
            db.commit()
            
    except Exception as e:
        logger.error(f"Error scanning emails for user={user_id}: {e}")
    finally:
        db.close()

def setup_user_schedules(user_id: str):
    """
    Đăng ký cron jobs cho một user.
    """
    for schedule in SCAN_SCHEDULE:
        job_id = f"email_scan_{user_id}_{schedule['label']}"
        scheduler.add_job(
            func=scan_academic_emails,
            trigger=CronTrigger(hour=schedule["hour"], minute=schedule["minute"]),
            id=job_id,
            args=[user_id, schedule["label"]],
            replace_existing=True,
        )
    logger.info(f"Registered {len(SCAN_SCHEDULE)} schedule jobs for user={user_id}")

def init_scheduler():
    """
    Khởi động scheduler khi app start và đăng ký jobs cho tất cả users.
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("Email Scheduler started.")
        
        # Đăng ký cho tất cả user hiện có
        db = SessionLocal()
        try:
            users = db.query(User).all()
            for u in users:
                setup_user_schedules(u.id)
        except Exception as e:
            logger.error(f"Failed to init schedules for users: {e}")
        finally:
            db.close()
