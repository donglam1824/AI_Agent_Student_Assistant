"""
api/v1/router.py
----------------
Aggregates all v1 API routers.
"""

from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.chat import router as chat_router
from api.v1.documents import router as documents_router
from api.v1.calendar import router as calendar_router
from api.v1.notes import router as notes_router
from api.v1.email import router as email_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(calendar_router)
api_router.include_router(notes_router)
api_router.include_router(email_router)
