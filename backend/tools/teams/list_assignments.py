"""
tools/teams/list_assignments.py
-------------------------------
LangChain tool to list Microsoft Education assignments.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_class_assignments(class_id: str, limit: int = 20, config: RunnableConfig = None) -> str:
    """
    Liet ke bai tap trong mot lop Microsoft Education/Teams.

    Args:
        class_id: ID cua Education class.
        limit: So bai tap toi da can lay.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    try:
        from services.teams_service import get_teams_service

        assignments = asyncio.run(
            get_teams_service(user_id=user_id).list_assignments(class_id=class_id, limit=limit)
        )
        if not assignments:
            return f"Khong co bai tap nao trong lop {class_id}."

        lines = [f"Danh sach {len(assignments)} bai tap:"]
        for assignment in assignments:
            due = assignment.due_date_time or "Chua co han nop"
            lines.append(
                f"- [{assignment.id}] {assignment.display_name}\n"
                f"  Trang thai: {assignment.status or 'unknown'} | Han nop: {due}\n"
                f"  Mo ta: {assignment.instructions_preview[:240]}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing assignments class={class_id}: {e}")
        return f"Loi khi lay bai tap Teams: {e}"
