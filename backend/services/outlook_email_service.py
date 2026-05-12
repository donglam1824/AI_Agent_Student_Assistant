"""
services/outlook_email_service.py
---------------------------------
Compatibility wrapper for Outlook email via Microsoft Graph.
"""

from services.graph_email_service import GraphEmailService as OutlookEmailService

__all__ = ["OutlookEmailService"]
