"""
api/v1/email_notifications.py
-----------------------------
SSE Endpoint để push notifications về email mới (urgent, morning briefs)
đến Frontend theo thời gian thực.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator
import json

from db.models import User
from api.deps import get_current_user
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

@router.get("/stream")
async def stream_notifications(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    SSE stream endpoint for email notifications.
    Client connects here to receive real-time updates.
    """
    logger.info(f"Client connected to SSE stream: user={current_user.id}")
    return StreamingResponse(
        sse_generator(request, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
