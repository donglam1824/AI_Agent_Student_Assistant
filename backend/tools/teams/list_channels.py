"""
tools/teams/list_channels.py
----------------------------
LangChain tool to list channels in a Microsoft Team.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_team_channels(team_id: str, limit: int = 20, config: RunnableConfig = None) -> str:
    """
    Liet ke cac kenh trong mot Microsoft Team/lop hoc.

    Args:
        team_id: ID cua Team/lop hoc.
        limit: So kenh toi da can lay.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    try:
        from services.teams_service import get_teams_service

        channels = asyncio.run(get_teams_service(user_id=user_id).list_channels(team_id=team_id, limit=limit))
        if not channels:
            return f"Khong tim thay kenh nao trong Team {team_id}."

        lines = [f"Danh sach {len(channels)} kenh trong Team {team_id}:"]
        for channel in channels:
            lines.append(
                f"- [{channel.id}] {channel.display_name}"
                + (f" | {channel.description}" if channel.description else "")
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing Teams channels team={team_id}: {e}")
        return f"Loi khi lay danh sach kenh Teams: {e}"
