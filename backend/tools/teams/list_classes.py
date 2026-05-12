"""
tools/teams/list_classes.py
---------------------------
LangChain tool to list Microsoft Education classes.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_education_classes(limit: int = 20, config: RunnableConfig = None) -> str:
    """
    Liet ke cac lop Microsoft Education de lay class_id cho bai tap.

    Args:
        limit: So lop toi da can lay.
    """
    _ = config
    try:
        from services.teams_service import get_teams_service

        classes = asyncio.run(get_teams_service().list_classes(limit=limit))
        if not classes:
            return "Khong tim thay lop Microsoft Education nao."

        lines = [f"Danh sach {len(classes)} lop Microsoft Education:"]
        for cls in classes:
            lines.append(
                f"- [{cls.id}] {cls.display_name}"
                + (f" | {cls.description}" if cls.description else "")
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing education classes: {e}")
        return f"Loi khi lay danh sach lop Education: {e}"
