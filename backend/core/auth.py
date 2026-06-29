"""
Xác thực Microsoft Graph bằng Azure Identity.
"""

from functools import lru_cache

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

from config.settings import settings
from core.logger import logger

CALENDAR_SCOPES = ["https://graph.microsoft.com/.default"]


@lru_cache(maxsize=1)
def get_graph_client() -> GraphServiceClient:
    """Khởi tạo và cache GraphServiceClient từ credentials trong settings"""
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


@lru_cache(maxsize=1)
def get_graph_credential() -> ClientSecretCredential:
    """Lấy credentials Azure cho các REST call trực tiếp tới Graph"""
    if not all([settings.azure_client_id, settings.azure_client_secret, settings.azure_tenant_id]):
        raise EnvironmentError(
            "Missing Azure credentials. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID in your .env file."
        )

    return ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )


def get_graph_access_token() -> str:
    """Lấy access token cho Microsoft Graph"""
    return get_graph_credential().get_token("https://graph.microsoft.com/.default").token
