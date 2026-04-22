"""
models/email.py
---------------
Pydantic schemas for Email.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

class EmailCreate(BaseModel):
    """Input model for sending a new email."""
    subject: str = Field(..., description="Subject of the email")
    body: str = Field(..., description="Body content of the email")
    to_recipients: List[str] = Field(..., description="List of recipient email addresses")
    cc_recipients: Optional[List[str]] = Field(default=None, description="List of CC email addresses")

class EmailMessage(BaseModel):
    """Output model representing an email message returned from the Graph API."""
    id: str = Field(..., description="Graph email ID")
    subject: str
    body_preview: str = Field(..., description="Preview of the email body")
    sender: str = Field(..., description="Sender's email address")
    received_date_time: str = Field(..., description="When the email was received")
    
    class Config:
        from_attributes = True
