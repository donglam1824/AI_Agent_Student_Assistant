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
from services.google_email_service import GoogleEmailService
from services.email_analyzer import analyze_and_store_emails

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
            
        email_svc = GoogleEmailService(user_id)
        emails = email_svc.get_emails_since(last_scan, limit=20)
        
        if emails:
            # Lọc email học thuật theo domains
            academic_domains = []
            if pref and pref.academic_domains:
                import json
                try:
                    academic_domains = json.loads(pref.academic_domains)
                except:
                    pass
            
            if not academic_domains:
                # Default
                academic_domains = ["@hcmus.edu.vn", "@hcmut.edu.vn", "@ueh.edu.vn", "@edu.vn", "school", "university"]
                
            filtered_emails = []
            for e in emails:
                sender = e['sender'].lower()
                is_academic = False
                for domain in academic_domains:
                    if domain in sender:
                        is_academic = True
                        break
                
                # Nơi này có thể gọi thêm LLM Classifier cho bước 2 như trong spec
                # Tạm thời dựa vào domain/từ khóa sender để filter nhanh
                if is_academic or "thầy" in sender or "cô" in sender or "teacher" in sender:
                    filtered_emails.append(e)
            
            if filtered_emails:
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
