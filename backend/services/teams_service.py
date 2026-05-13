"""
services/teams_service.py
-------------------------
Read-only Microsoft Teams and Education service backed by Microsoft Graph.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import requests

from core.logger import logger
from models.teams import ChannelInfo, EducationClassInfo, TeamInfo, TeamsAssignment, TeamsMessage


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


class BaseTeamsService(ABC):
    @abstractmethod
    async def list_teams(self, limit: int = 20) -> List[TeamInfo]: ...

    @abstractmethod
    async def list_channels(self, team_id: str, limit: int = 20) -> List[ChannelInfo]: ...

    @abstractmethod
    async def list_classes(self, limit: int = 20) -> List[EducationClassInfo]: ...

    @abstractmethod
    async def list_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 10,
    ) -> List[TeamsMessage]: ...

    @abstractmethod
    async def list_assignments(self, class_id: str, limit: int = 20) -> List[TeamsAssignment]: ...


class MockTeamsService(BaseTeamsService):
    async def list_teams(self, limit: int = 20) -> List[TeamInfo]:
        return [
            TeamInfo(id="mock-team-ai", display_name="Nhap mon AI", description="Lop hoc mau"),
            TeamInfo(id="mock-team-db", display_name="Co so du lieu", description="Lop hoc mau"),
        ][:limit]

    async def list_channels(self, team_id: str, limit: int = 20) -> List[ChannelInfo]:
        return [
            ChannelInfo(id="general", team_id=team_id, display_name="General"),
            ChannelInfo(id="assignments", team_id=team_id, display_name="Bai tap"),
        ][:limit]

    async def list_classes(self, limit: int = 20) -> List[EducationClassInfo]:
        return [
            EducationClassInfo(id="mock-class-ai", display_name="Nhap mon AI"),
            EducationClassInfo(id="mock-class-db", display_name="Co so du lieu"),
        ][:limit]

    async def list_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 10,
    ) -> List[TeamsMessage]:
        return [
            TeamsMessage(
                id="mock-message-1",
                team_id=team_id,
                channel_id=channel_id,
                body_preview="Thong bao: nop bai tap lon truoc 23:59 thu Sau.",
                sender="giangvien@truong.edu.vn",
                created_date_time="2026-05-12T02:00:00Z",
            )
        ][:limit]

    async def list_assignments(self, class_id: str, limit: int = 20) -> List[TeamsAssignment]:
        return [
            TeamsAssignment(
                id="mock-assignment-1",
                class_id=class_id,
                display_name="Bai tap lon cuoi ky",
                status="assigned",
                due_date_time="2026-05-20T16:59:00Z",
                instructions_preview="Hoan thanh bao cao va nop file PDF.",
            )
        ][:limit]


class GraphTeamsService(BaseTeamsService):
    """Read-only Teams/Education implementation using Microsoft Graph REST."""

    def __init__(self, user_id: str | None = None) -> None:
        from config.settings import settings
        self._local_user_id = user_id
        self._token = self._get_token()
        self._user_id = settings.graph_user_id

    def _get_token(self) -> str:
        if self._local_user_id:
            from db.database import SessionLocal
            from services.microsoft_oauth_service import get_user_microsoft_access_token

            db = SessionLocal()
            try:
                return get_user_microsoft_access_token(db, self._local_user_id)
            finally:
                db.close()

        from core.auth import get_graph_access_token
        return get_graph_access_token()

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{GRAPH_ROOT}{path}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
            params=params,
            timeout=30,
        )
        if response.status_code >= 400:
            logger.error(f"[Teams Graph] GET {url} failed: {response.status_code} {response.text}")
            response.raise_for_status()
        return response.json()

    async def list_teams(self, limit: int = 20) -> List[TeamInfo]:
        logger.info(f"[Teams Graph] Listing teams for user={self._user_id}")
        path = "/me/joinedTeams" if self._local_user_id else f"/users/{self._user_id}/joinedTeams"
        data = self._get(path, {"$top": min(limit, 50)})
        return [
            TeamInfo(
                id=item.get("id", ""),
                display_name=item.get("displayName") or "(Khong co ten lop)",
                description=item.get("description"),
                web_url=item.get("webUrl"),
            )
            for item in data.get("value", [])
        ]

    async def list_channels(self, team_id: str, limit: int = 20) -> List[ChannelInfo]:
        logger.info(f"[Teams Graph] Listing channels for team={team_id}")
        data = self._get(f"/teams/{team_id}/channels", {"$top": min(limit, 50)})
        return [
            ChannelInfo(
                id=item.get("id", ""),
                team_id=team_id,
                display_name=item.get("displayName") or "(Khong co ten kenh)",
                description=item.get("description"),
                web_url=item.get("webUrl"),
            )
            for item in data.get("value", [])
        ]

    async def list_classes(self, limit: int = 20) -> List[EducationClassInfo]:
        logger.info("[Teams Graph] Listing education classes")
        path = "/education/me/classes" if self._local_user_id else "/education/classes"
        data = self._get(path, {"$top": min(limit, 50)})
        return [
            EducationClassInfo(
                id=item.get("id", ""),
                display_name=item.get("displayName") or "(Khong co ten lop)",
                description=item.get("description"),
                mail_nickname=item.get("mailNickname"),
            )
            for item in data.get("value", [])
        ]

    async def list_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 10,
    ) -> List[TeamsMessage]:
        logger.info(f"[Teams Graph] Listing messages team={team_id} channel={channel_id}")
        data = self._get(
            f"/teams/{team_id}/channels/{channel_id}/messages",
            {"$top": min(limit, 50)},
        )
        messages: list[TeamsMessage] = []
        for item in data.get("value", []):
            body = item.get("body") or {}
            sender = item.get("from") or {}
            user = sender.get("user") or {}
            messages.append(
                TeamsMessage(
                    id=item.get("id", ""),
                    team_id=team_id,
                    channel_id=channel_id,
                    subject=item.get("subject"),
                    summary=item.get("summary"),
                    body_preview=_strip_html(body.get("content"))[:500],
                    sender=user.get("displayName") or user.get("userIdentityType") or "unknown",
                    created_date_time=item.get("createdDateTime") or "",
                    web_url=item.get("webUrl"),
                )
            )
        return messages

    async def list_assignments(self, class_id: str, limit: int = 20) -> List[TeamsAssignment]:
        logger.info(f"[Teams Graph] Listing assignments for class={class_id}")
        data = self._get(f"/education/classes/{class_id}/assignments", {"$top": min(limit, 50)})
        assignments: list[TeamsAssignment] = []
        for item in data.get("value", []):
            instructions = item.get("instructions") or {}
            content = instructions.get("content") if isinstance(instructions, dict) else ""
            due = item.get("dueDateTime") or {}
            assignments.append(
                TeamsAssignment(
                    id=item.get("id", ""),
                    class_id=class_id,
                    display_name=item.get("displayName") or "(Khong co ten bai tap)",
                    status=item.get("status"),
                    due_date_time=due.get("dateTime") if isinstance(due, dict) else None,
                    instructions_preview=_strip_html(content)[:500],
                    web_url=item.get("webUrl"),
                )
            )
        return assignments[:limit]


def get_teams_service(user_id: str | None = None) -> BaseTeamsService:
    from config.settings import settings

    provider = settings.teams_provider.lower().strip()
    if provider == "mock" or settings.mock_graph:
        return MockTeamsService()
    if provider == "msgraph":
        return GraphTeamsService(user_id=user_id)
    raise ValueError(f"Unknown TEAMS_PROVIDER={provider!r}")
