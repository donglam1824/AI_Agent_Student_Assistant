"""
services/academic_filter.py
----------------------------
Bộ lọc email học thuật đa tầng, dùng chung cho cả scheduler và chat tools.

Phân loại email qua 4 tầng:
  1. Domain trường đại học
  2. Subdomain LMS / học vụ
  3. Từ khóa trong sender
  4. Từ khóa trong subject / body (bonus signal)
"""

from __future__ import annotations

import json
import re
from typing import Optional

from core.logger import logger
from models.email import EmailMessage

# ── Tầng 1: Domain trường đại học mặc định ──────────────────────────────

DEFAULT_ACADEMIC_DOMAINS: list[str] = [
    "@edu.vn",
    "@hust.edu.vn",
    "@hcmut.edu.vn",
    "@hcmus.edu.vn",
    "@fit.hcmus.edu.vn",
    "@uit.edu.vn",
    "@uel.edu.vn",
    "@ueh.edu.vn",
    "@vnu.edu.vn",
    "@vnuhcm.edu.vn",
    "@neu.edu.vn",
    "@ftu.edu.vn",
    "@fpt.edu.vn",
    "@rmit.edu.vn",
]

# ── Tầng 2: Subdomain patterns (LMS, học vụ, khoa) ─────────────────────

ACADEMIC_SUBDOMAIN_PATTERNS: list[str] = [
    r"lms\.",
    r"elearning\.",
    r"canvas\.",
    r"moodle\.",
    r"student\.",
    r"portal\.",
    r"courses\.",
    r"fit\.",
    r"blackboard\.",
    r"classroom\.",
    # Also match common LMS platforms directly
    r"canvas\.instructure\.com",
    r"coursera\.org",
    r"edx\.org",
]

# ── Tầng 3: Từ khóa trong sender ────────────────────────────────────────

ACADEMIC_SENDER_KEYWORDS: list[str] = [
    "thầy", "cô", "teacher", "professor", "prof.",
    "giảng viên", "giang vien",
    "phòng đào tạo", "phong dao tao",
    "khoa ", "ban giám hiệu", "ban giam hieu",
    "academic", "dean", "registrar",
    "noreply@lms", "noreply@elearning",
]

# ── Tầng 4: Từ khóa trong subject / body ────────────────────────────────

ACADEMIC_CONTENT_KEYWORDS_VI: list[str] = [
    "lịch học", "lich hoc",
    "bài tập", "bai tap",
    "nộp bài", "nop bai",
    "điểm", "diem",
    "thi ", " thi",
    "học phần", "hoc phan",
    "đăng ký học", "dang ky hoc",
    "học phí", "hoc phi",
    "luận văn", "luan van",
    "thời khóa biểu", "thoi khoa bieu",
    "học kỳ", "hoc ky",
    "sinh viên", "sinh vien",
    "giảng viên", "giang vien",
    "đồ án", "do an",
    "tiểu luận", "tieu luan",
    "thực hành", "thuc hanh",
    "phòng học", "phong hoc",
]

ACADEMIC_CONTENT_KEYWORDS_EN: list[str] = [
    "assignment", "deadline", "submission",
    "exam", "quiz", "grade", "grading",
    "course", "class", "lecture", "seminar",
    "thesis", "tuition", "scholarship",
    "registration", "schedule", "syllabus",
    "midterm", "final exam", "gpa",
    "homework", "lab report", "project",
]

ALL_CONTENT_KEYWORDS = ACADEMIC_CONTENT_KEYWORDS_VI + ACADEMIC_CONTENT_KEYWORDS_EN


# ── Classification logic ────────────────────────────────────────────────

def _extract_email_address(sender: str) -> str:
    """Trích xuất địa chỉ email thuần từ chuỗi sender, vd 'Name <a@b.com>' → 'a@b.com'."""
    if "<" in sender and ">" in sender:
        return sender.split("<")[1].split(">")[0].lower()
    return sender.lower().strip()


def _match_domain(email_addr: str, domains: list[str]) -> bool:
    """Kiểm tra email address có thuộc domain nào trong danh sách."""
    for domain in domains:
        if email_addr.endswith(domain.lower()):
            return True
    return False


def _match_subdomain_pattern(email_addr: str) -> bool:
    """Kiểm tra email address hoặc sender có chứa subdomain pattern học thuật."""
    for pattern in ACADEMIC_SUBDOMAIN_PATTERNS:
        if re.search(pattern, email_addr, re.IGNORECASE):
            return True
    return False


def _match_sender_keywords(sender: str) -> bool:
    """Kiểm tra chuỗi sender (bao gồm tên hiển thị) có chứa từ khóa học thuật."""
    sender_lower = sender.lower()
    for keyword in ACADEMIC_SENDER_KEYWORDS:
        if keyword in sender_lower:
            return True
    return False


def _match_content_keywords(subject: str, body_preview: str) -> bool:
    """Kiểm tra subject hoặc body preview có chứa từ khóa học thuật."""
    text = (subject + " " + body_preview).lower()
    for keyword in ALL_CONTENT_KEYWORDS:
        if keyword in text:
            return True
    return False


def classify_email(
    email: EmailMessage,
    user_domains: list[str] | None = None,
    user_keywords: list[str] | None = None,
) -> str:
    """
    Phân loại một email thành 3 mức:
      - 'academic':        Chắc chắn là email học thuật (match domain/subdomain/sender)
      - 'likely_academic':  Có thể là email học thuật (match content keywords)
      - 'non_academic':    Không phải email học thuật

    Args:
        email: EmailMessage object.
        user_domains: Danh sách domain tùy chỉnh của user (ngoài default).
        user_keywords: Danh sách keyword tùy chỉnh của user.
    """
    sender_raw = email.sender or ""
    email_addr = _extract_email_address(sender_raw)
    subject = email.subject or ""
    body_preview = email.body_preview or ""

    # Merge user custom domains với default
    all_domains = list(DEFAULT_ACADEMIC_DOMAINS)
    if user_domains:
        all_domains.extend(user_domains)

    # Tầng 1: Domain trường đại học
    if _match_domain(email_addr, all_domains):
        return "academic"

    # Tầng 2: Subdomain patterns (lms.*, elearning.*, canvas.*, ...)
    if _match_subdomain_pattern(email_addr):
        return "academic"

    # Tầng 3: Từ khóa trong sender
    if _match_sender_keywords(sender_raw):
        return "academic"

    # Tầng 4: Từ khóa trong subject / body (bonus signal)
    all_keywords = list(ALL_CONTENT_KEYWORDS)
    if user_keywords:
        all_keywords.extend(user_keywords)

    text = (subject + " " + body_preview).lower()
    for keyword in all_keywords:
        if keyword.lower() in text:
            return "likely_academic"

    return "non_academic"


def filter_academic_emails(
    emails: list[EmailMessage],
    user_id: str | None = None,
) -> tuple[list[EmailMessage], list[EmailMessage]]:
    """
    Lọc danh sách email thành 2 nhóm: học thuật và không học thuật.
    Email 'likely_academic' được gộp vào nhóm học thuật.

    Returns:
        (academic_emails, non_academic_emails)
    """
    user_domains, user_keywords = _get_user_academic_config(user_id)

    academic: list[EmailMessage] = []
    non_academic: list[EmailMessage] = []

    for email in emails:
        classification = classify_email(email, user_domains, user_keywords)
        if classification in ("academic", "likely_academic"):
            academic.append(email)
        else:
            non_academic.append(email)

    logger.info(
        f"[AcademicFilter] user={user_id}: "
        f"{len(academic)} academic, {len(non_academic)} non-academic "
        f"out of {len(emails)} total"
    )
    return academic, non_academic


def _get_user_academic_config(
    user_id: str | None,
) -> tuple[list[str], list[str]]:
    """
    Lấy danh sách domain và keyword tùy chỉnh từ EmailPreference.
    Trả về (custom_domains, custom_keywords).
    """
    if not user_id:
        return [], []

    try:
        from db.database import SessionLocal
        from db.crud import get_email_preference

        db = SessionLocal()
        try:
            pref = get_email_preference(db, user_id)
            if not pref:
                return [], []

            custom_domains: list[str] = []
            if pref.academic_domains:
                try:
                    custom_domains = json.loads(pref.academic_domains)
                except (json.JSONDecodeError, TypeError):
                    pass

            custom_keywords: list[str] = []
            if hasattr(pref, "academic_keywords") and pref.academic_keywords:
                try:
                    custom_keywords = json.loads(pref.academic_keywords)
                except (json.JSONDecodeError, TypeError):
                    pass

            return custom_domains, custom_keywords
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[AcademicFilter] Failed to load user config: {e}")
        return [], []
