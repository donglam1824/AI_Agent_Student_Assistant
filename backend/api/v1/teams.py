"""
api/v1/teams.py
---------------
Microsoft Teams read-only proxy endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from db.models import User
from models.teams import (
    ChannelInfo,
    EducationClassInfo,
    TeamInfo,
    TeamsAssignment,
    TeamsMessage,
)
from core.logger import logger


router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=list[TeamInfo])
async def list_teams(limit: int = 20, current_user: User = Depends(get_current_user)):
    try:
        from services.teams_service import get_teams_service

        return await get_teams_service(user_id=current_user.id).list_teams(limit=limit)
    except Exception as e:
        logger.error(f"Teams list error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi lay danh sach Teams: {str(e)}")


@router.get("/{team_id}/channels", response_model=list[ChannelInfo])
async def list_channels(
    team_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    try:
        from services.teams_service import get_teams_service

        return await get_teams_service(user_id=current_user.id).list_channels(team_id=team_id, limit=limit)
    except Exception as e:
        logger.error(f"Teams channel list error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi lay danh sach kenh: {str(e)}")


@router.get("/classes", response_model=list[EducationClassInfo])
async def list_classes(limit: int = 20, current_user: User = Depends(get_current_user)):
    try:
        from services.teams_service import get_teams_service

        return await get_teams_service(user_id=current_user.id).list_classes(limit=limit)
    except Exception as e:
        logger.error(f"Teams classes list error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi lay danh sach lop: {str(e)}")


@router.get("/{team_id}/channels/{channel_id}/messages", response_model=list[TeamsMessage])
async def list_channel_messages(
    team_id: str,
    channel_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    try:
        from services.teams_service import get_teams_service

        return await get_teams_service(user_id=current_user.id).list_channel_messages(
            team_id=team_id,
            channel_id=channel_id,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Teams message list error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi lay tin nhan Teams: {str(e)}")


@router.get("/classes/{class_id}/assignments", response_model=list[TeamsAssignment])
async def list_assignments(
    class_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    try:
        from services.teams_service import get_teams_service

        return await get_teams_service(user_id=current_user.id).list_assignments(class_id=class_id, limit=limit)
    except Exception as e:
        logger.error(f"Teams assignment list error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi khi lay bai tap Teams: {str(e)}")
