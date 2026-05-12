"""
tools/teams/list_messages.py
----------------------------
LangChain tool to list recent Microsoft Teams channel messages.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_team_messages(
    team_id: str,
    channel_id: str,
    limit: int = 10,
    config: RunnableConfig = None,
) -> str:
    """
    Lay cac tin nhan moi trong mot kenh Teams.

    Args:
        team_id: ID cua Team/lop hoc.
        channel_id: ID cua kenh.
        limit: So tin nhan toi da can lay.
    """
    _ = config
    try:
        from services.teams_service import get_teams_service

        messages = asyncio.run(
            get_teams_service().list_channel_messages(
                team_id=team_id,
                channel_id=channel_id,
                limit=limit,
            )
        )
        if not messages:
            return "Khong co tin nhan nao trong kenh nay."

        lines = [f"{len(messages)} tin nhan Teams gan day:"]
        for message in messages:
            title = message.subject or message.summary or "(khong co tieu de)"
            lines.append(
                f"- [{message.id}] {title}\n"
                f"  Tu: {message.sender} | Luc: {message.created_date_time}\n"
                f"  Noi dung: {message.body_preview[:240]}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing Teams messages team={team_id} channel={channel_id}: {e}")
        return f"Loi khi lay tin nhan Teams: {e}"
