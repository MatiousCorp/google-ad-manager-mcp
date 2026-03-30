"""Google Ad Manager Client - Authentication and connection management."""

import logging
from typing import Optional
from googleads import ad_manager, oauth2

logger = logging.getLogger(__name__)


class GAMClient:
    """Google Ad Manager API client wrapper."""

    DEFAULT_API_VERSION = "v202602"

    def __init__(
        self,
        credentials_path: str,
        network_code: str,
        application_name: str = "GAM MCP Server",
        api_version: Optional[str] = None,
    ):
        """Initialize the GAM client.

        Args:
            credentials_path: Path to service account JSON credentials file
            network_code: Ad Manager network code
            application_name: Application name for API requests
            api_version: GAM API version override (e.g. "v202602"). Defaults to DEFAULT_API_VERSION.
        """
        self.credentials_path = credentials_path
        self.network_code = network_code
        self.application_name = application_name
        self._client: Optional[ad_manager.AdManagerClient] = None
        self._api_version = api_version or self.DEFAULT_API_VERSION

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

    def get_data_downloader(self):
        """Get the data downloader for reports.

        Returns:
            The DataDownloader instance for downloading reports
        """
        return self.client.GetDataDownloader(version=self._api_version)


# Multi-network client registry
_gam_clients: dict[str, GAMClient] = {}
_default_network_code: Optional[str] = None
_credentials_path: Optional[str] = None
_application_name: str = "GAM MCP Server"
_api_version_override: Optional[str] = None
_allowed_network_codes: set[str] = set()


def is_gam_client_initialized() -> bool:
    """Check if the GAM client has been initialized.

    Returns:
        True if the client is initialized, False otherwise
    """
    return _default_network_code is not None


def get_gam_client(network_code: Optional[str] = None) -> GAMClient:
    """Get a GAM client instance for the given network code.

    Args:
        network_code: Optional network code. If not provided, uses the default network.

    Returns:
        The GAM client instance for the requested network

    Raises:
        RuntimeError: If the client has not been initialized
        ValueError: If the network code is not in the allowed list
    """
    if _default_network_code is None:
        raise RuntimeError(
            "GAM client not initialized. Call init_gam_client() first."
        )

    target_code = network_code or _default_network_code

    if target_code not in _allowed_network_codes:
        raise ValueError(
            f"Network code '{target_code}' is not allowed. "
            f"Allowed networks: {sorted(_allowed_network_codes)}"
        )

    if target_code not in _gam_clients:
        logger.info(f"Creating GAM client for network {target_code}")
        _gam_clients[target_code] = GAMClient(
            _credentials_path, target_code, _application_name,
            api_version=_api_version_override,
        )

    return _gam_clients[target_code]


def init_gam_client(
    credentials_path: str,
    network_code: str,
    application_name: str = "GAM MCP Server",
    allowed_network_codes: Optional[set[str]] = None,
    api_version: Optional[str] = None,
) -> GAMClient:
    """Initialize the GAM client registry.

    Args:
        credentials_path: Path to service account JSON credentials file
        network_code: Default Ad Manager network code
        application_name: Application name for API requests
        allowed_network_codes: Optional set of additional allowed network codes
        api_version: GAM API version override (e.g. "v202602"). If None, uses GAMClient default.

    Returns:
        The initialized default GAM client
    """
    global _gam_clients, _default_network_code, _credentials_path
    global _application_name, _allowed_network_codes, _api_version_override

    _credentials_path = credentials_path
    _default_network_code = network_code
    _application_name = application_name
    _api_version_override = api_version

    # Build allowed set: always includes the default
    _allowed_network_codes = {network_code}
    if allowed_network_codes:
        _allowed_network_codes.update(allowed_network_codes)

    # Create the default client eagerly
    client = GAMClient(credentials_path, network_code, application_name, api_version=api_version)
    _gam_clients[network_code] = client
    logger.info(f"GAM client initialized for default network {network_code} (API {client.api_version})")
    if len(_allowed_network_codes) > 1:
        logger.info(f"Additional allowed networks: {sorted(_allowed_network_codes - {network_code})}")
    return client
