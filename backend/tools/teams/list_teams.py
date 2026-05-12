"""
tools/teams/list_teams.py
-------------------------
LangChain tool to list Microsoft Teams classes/teams.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_teams(limit: int = 20, config: RunnableConfig = None) -> str:
    """
    Liet ke cac lop/nhom Microsoft Teams ma tai khoan Graph co the truy cap.

    Args:
        limit: So lop/nhom toi da can lay.
    """
    _ = config
    try:
        from services.teams_service import get_teams_service

        teams = asyncio.run(get_teams_service().list_teams(limit=limit))
        if not teams:
            return "Khong tim thay lop/nhom Teams nao."

        lines = [f"Danh sach {len(teams)} lop/nhom Teams:"]
        for team in teams:
            lines.append(
                f"- [{team.id}] {team.display_name}"
                + (f" | {team.description}" if team.description else "")
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing Teams: {e}")
        return f"Loi khi lay danh sach Teams: {e}"
