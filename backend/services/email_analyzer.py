"""
backend/services/email_analyzer.py
----------------------------------
Dịch vụ phân tích email nền. Sử dụng LangChain và các tools để phân loại
email, tóm tắt và trích xuất deadline.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from core.logger import logger
from db.crud import create_email_summary, update_email_summary_calendar_event
from agents.email.tools.analyze_priority import analyze_priority
from agents.email.tools.extract_deadline import extract_deadline
from agents.email.tools.create_reminder import create_reminder
from core.llm_manager import llm_manager
from db.database import SessionLocal

def analyze_and_store_emails(user_id: str, emails: List[Dict[str, Any]], scan_session: str):
    """
    Phân tích danh sách email và lưu kết quả vào Database.
    """
    logger.info(f"Analyzing {len(emails)} emails for user={user_id} (session={scan_session})")
    db = SessionLocal()
    try:
        # Lấy mô hình LLM để tóm tắt
        llm = llm_manager.get_model(task="email_summary")
        
        for email_data in emails:
            gmail_id = email_data['id']
            subject = email_data['subject']
            sender = email_data['sender']
            body = email_data['body']
            snippet = email_data['snippet']
            
            # 1. Phân tích ưu tiên
            priority = analyze_priority.invoke({
                "subject": subject,
                "sender": sender,
                "body": body
            })
            
            # 2. Tóm tắt nội dung
            prompt = f"Tóm tắt email sau trong 1-2 câu ngắn gọn:\nChủ đề: {subject}\nNgười gửi: {sender}\nNội dung: {snippet}"
            summary_response = llm.invoke(prompt)
            summary_text = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            
            # 3. Trích xuất deadline
            deadline_result_str = extract_deadline.invoke({"text": body})
            deadline_info = json.loads(deadline_result_str)
            
            deadline_date = None
            if deadline_info.get("has_deadline") and deadline_info.get("deadline_date"):
                try:
                    date_str = deadline_info["deadline_date"]
                    time_str = deadline_info.get("deadline_time", "23:59")
                    dt_str = f"{date_str} {time_str}"
                    deadline_date = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                except Exception as e:
                    logger.error(f"Error parsing deadline: {e}")
            
            # 4. Lưu vào Database
            # Trích xuất địa chỉ email từ chuỗi sender, vd "Name <email@domain.com>"
            sender_email = sender
            if "<" in sender and ">" in sender:
                sender_email = sender.split("<")[1].split(">")[0]
            
            # Chuyển đổi date string của email thành datetime (thử bắt format)
            from email.utils import parsedate_to_datetime
            try:
                received_at = parsedate_to_datetime(email_data['date'])
            except:
                received_at = datetime.now(timezone.utc)

            summary_record = create_email_summary(
                db=db,
                user_id=user_id,
                gmail_id=gmail_id,
                subject=subject,
                sender=sender,
                sender_email=sender_email,
                received_at=received_at,
                scan_session=scan_session,
                summary=summary_text,
                priority=priority,
                deadline=deadline_date,
                requires_reply=(priority == "follow_up")
            )
            
            # 5. Nếu có deadline, tự động tạo calendar event
            if deadline_date and deadline_info.get("task_name"):
                reminder_result = create_reminder.invoke({
                    "task_name": deadline_info["task_name"],
                    "date_str": deadline_info["deadline_date"],
                    "time_str": deadline_info.get("deadline_time"),
                    "description": f"Từ email: {subject} ({sender})"
                })
                # Trích xuất event_id (giả lập)
                if "Event ID:" in reminder_result:
                    event_id = reminder_result.split("Event ID: ")[1].strip()
                    update_email_summary_calendar_event(db, summary_record.id, event_id)
                logger.info(f"Auto-created reminder for email {gmail_id}")
                
    except Exception as e:
        logger.error(f"Error in analyze_and_store_emails: {e}")
    finally:
        db.close()
