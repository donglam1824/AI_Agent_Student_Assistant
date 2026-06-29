"""
api/v1/email_notifications.py
-----------------------------
SSE Endpoint để push notifications về email mới (urgent, morning briefs)
đến Frontend theo thời gian thực.

NOTE: EventSource API (browser) KHÔNG hỗ trợ gửi custom headers.
      Vì vậy endpoint này xác thực qua query param `?token=xxx`
      thay vì Authorization header.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
from typing import AsyncGenerator, Optional
import json

from db.database import get_db
from db.models import User
from db import crud
from core.security import verify_token
from core.logger import logger

router = APIRouter(prefix="/email/notifications", tags=["Email Notifications"])

# In-memory pub/sub queues for SSE (Demo)
# Trong production nên dùng Redis Pub/Sub
user_queues = {}

def get_user_queue(user_id: str) -> asyncio.Queue:
    if user_id not in user_queues:
        user_queues[user_id] = asyncio.Queue()
    return user_queues[user_id]

async def push_email_notification(user_id: str, message: dict):
    """
    Push a message to the user's SSE queue.
    Gọi hàm này từ background service khi quét xong email.
    """
    if user_id in user_queues:
        await user_queues[user_id].put(message)
        logger.info(f"Pushed notification to user {user_id}")

async def sse_generator(request: Request, user_id: str) -> AsyncGenerator[str, None]:
    queue = get_user_queue(user_id)
    try:
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
                
            try:
                # Wait for message with timeout to allow disconnect detection
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(message)}\n\n"
            except asyncio.TimeoutError:
                # Send keep-alive heartbeat
                yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        logger.info(f"SSE disconnected for user {user_id}")
    finally:
        # Cleanup can be implemented here
        pass

async def _get_user_from_token(token: str, db: Session) -> User:
    """
    Xác thực user từ JWT token (dùng cho SSE endpoint
    vì EventSource không gửi được Authorization header).
    """
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
        )
    user = crud.get_user_by_id(db, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
        )
    return user

@router.get("/stream")
async def stream_notifications(
    request: Request,
    token: str = Query(..., description="JWT token for SSE authentication"),
    db: Session = Depends(get_db),
):
    """
    SSE stream endpoint for email notifications.
    Client connects here to receive real-time updates.

    Xác thực qua query param `?token=xxx` vì EventSource API
    không hỗ trợ custom headers (Authorization).
    """
    current_user = await _get_user_from_token(token, db)
    logger.info(f"Client connected to SSE stream: user={current_user.id}")
    return StreamingResponse(
        sse_generator(request, str(current_user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
