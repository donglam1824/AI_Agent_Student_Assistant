"""
core/auth.py
------------
Microsoft Graph authentication using Azure Identity.
Returns a ready-to-use GraphServiceClient.
"""

from functools import lru_cache

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

from config.settings import settings
from core.logger import logger

# Microsoft Graph scopes required for Calendar access
CALENDAR_SCOPES = ["https://graph.microsoft.com/.default"]


@lru_cache(maxsize=1)
def get_graph_client() -> GraphServiceClient:
    """
    Returns a cached GraphServiceClient authenticated with client credentials.
    Requires AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID in settings.
    """
    if not all([settings.azure_client_id, settings.azure_client_secret, settings.azure_tenant_id]):
        raise EnvironmentError(
            "Missing Azure credentials. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID in your .env file."
        )

    credential = ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )

    logger.info("Microsoft Graph client initialized successfully.")
    return GraphServiceClient(credentials=credential, scopes=CALENDAR_SCOPES)
