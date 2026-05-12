"""
models/teams.py
---------------
Pydantic schemas for Microsoft Teams / Education data.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TeamInfo(BaseModel):
    id: str = Field(..., description="Microsoft Teams team ID")
    display_name: str
    description: Optional[str] = None
    web_url: Optional[str] = None


class ChannelInfo(BaseModel):
    id: str = Field(..., description="Microsoft Teams channel ID")
    team_id: str
    display_name: str
    description: Optional[str] = None
    web_url: Optional[str] = None


class EducationClassInfo(BaseModel):
    id: str = Field(..., description="Microsoft Education class ID")
    display_name: str
    description: Optional[str] = None
    mail_nickname: Optional[str] = None


class TeamsMessage(BaseModel):
    id: str = Field(..., description="Teams channel message ID")
    team_id: str
    channel_id: str
    subject: Optional[str] = None
    summary: Optional[str] = None
    body_preview: str = ""
    sender: str = "unknown"
    created_date_time: str = ""
    web_url: Optional[str] = None


class TeamsAssignment(BaseModel):
    id: str = Field(..., description="Education assignment ID")
    class_id: str
    display_name: str
    status: Optional[str] = None
    due_date_time: Optional[str] = None
    instructions_preview: str = ""
    web_url: Optional[str] = None
