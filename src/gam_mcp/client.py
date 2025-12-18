"""Google Ad Manager Client - Authentication and connection management."""

import logging
from typing import Optional
from googleads import ad_manager, oauth2

logger = logging.getLogger(__name__)


class GAMClient:
    """Google Ad Manager API client wrapper."""

    def __init__(
        self,
        credentials_path: str,
        network_code: str,
        application_name: str = "GAM MCP Server"
    ):
        """Initialize the GAM client.

        Args:
            credentials_path: Path to service account JSON credentials file
            network_code: Ad Manager network code
            application_name: Application name for API requests
        """
        self.credentials_path = credentials_path
        self.network_code = network_code
        self.application_name = application_name
        self._client: Optional[ad_manager.AdManagerClient] = None
        self._api_version = "v202411"

    def _get_client(self) -> ad_manager.AdManagerClient:
        """Get or create the Ad Manager client."""
        if self._client is None:
            logger.info(f"Initializing GAM client for network {self.network_code}")

            oauth2_client = oauth2.GoogleServiceAccountClient(
                self.credentials_path,
                oauth2.GetAPIScope('ad_manager')
            )

            self._client = ad_manager.AdManagerClient(
                oauth2_client,
                self.application_name,
                network_code=self.network_code
            )

        return self._client

    @property
    def client(self) -> ad_manager.AdManagerClient:
        """Get the Ad Manager client."""
        return self._get_client()

    @property
    def api_version(self) -> str:
        """Get the API version."""
        return self._api_version

    def get_service(self, service_name: str):
        """Get a service from the Ad Manager client.

        Args:
            service_name: Name of the service (e.g., 'OrderService', 'LineItemService')

        Returns:
            The requested service
        """
        return self.client.GetService(service_name, version=self._api_version)

    def create_statement(self):
        """Create a new StatementBuilder.

        Returns:
            A new StatementBuilder instance
        """
        return ad_manager.StatementBuilder(version=self._api_version)


# Global client instance
_gam_client: Optional[GAMClient] = None


def get_gam_client() -> GAMClient:
    """Get the global GAM client instance.

    Returns:
        The GAM client instance

    Raises:
        RuntimeError: If the client has not been initialized
    """
    if _gam_client is None:
        raise RuntimeError(
            "GAM client not initialized. Call init_gam_client() first."
        )
    return _gam_client


def init_gam_client(
    credentials_path: str,
    network_code: str,
    application_name: str = "GAM MCP Server"
) -> GAMClient:
    """Initialize the global GAM client.

    Args:
        credentials_path: Path to service account JSON credentials file
        network_code: Ad Manager network code
        application_name: Application name for API requests

    Returns:
        The initialized GAM client
    """
    global _gam_client
    _gam_client = GAMClient(credentials_path, network_code, application_name)
    logger.info(f"GAM client initialized for network {network_code}")
    return _gam_client
