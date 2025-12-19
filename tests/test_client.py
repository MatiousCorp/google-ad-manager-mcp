"""Tests for GAM client module."""

import pytest
from unittest.mock import patch, MagicMock

from gam_mcp.client import (
    GAMClient,
    get_gam_client,
    init_gam_client,
)


class TestGAMClient:
    """Tests for GAMClient class."""

    @patch("gam_mcp.client.oauth2.GoogleServiceAccountClient")
    @patch("gam_mcp.client.ad_manager.AdManagerClient")
    def test_client_initialization(self, mock_ad_manager, mock_oauth2):
        """Test GAMClient initializes with correct parameters."""
        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
            application_name="Test App",
        )

        assert client.credentials_path == "/path/to/creds.json"
        assert client.network_code == "12345678"
        assert client.application_name == "Test App"
        assert client._client is None

    @patch("gam_mcp.client.oauth2.GoogleServiceAccountClient")
    @patch("gam_mcp.client.ad_manager.AdManagerClient")
    def test_client_lazy_initialization(self, mock_ad_manager, mock_oauth2):
        """Test client is lazily initialized on first access."""
        mock_oauth2_instance = MagicMock()
        mock_oauth2.return_value = mock_oauth2_instance

        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        # Client should not be initialized yet
        assert client._client is None

        # Access the client property
        _ = client.client

        # OAuth2 client should be created
        mock_oauth2.assert_called_once()

        # Ad Manager client should be created
        mock_ad_manager.assert_called_once_with(
            mock_oauth2_instance,
            "GAM MCP Server",
            network_code="12345678",
        )

    @patch("gam_mcp.client.oauth2.GoogleServiceAccountClient")
    @patch("gam_mcp.client.ad_manager.AdManagerClient")
    def test_client_reuses_instance(self, mock_ad_manager, mock_oauth2):
        """Test client reuses the same instance on multiple accesses."""
        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        # Access client multiple times
        _ = client.client
        _ = client.client
        _ = client.client

        # Should only create once
        mock_ad_manager.assert_called_once()

    def test_api_version(self):
        """Test API version is correctly set."""
        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )
        assert client.api_version == "v202411"

    @patch("gam_mcp.client.oauth2.GoogleServiceAccountClient")
    @patch("gam_mcp.client.ad_manager.AdManagerClient")
    def test_get_service(self, mock_ad_manager, mock_oauth2):
        """Test get_service calls the underlying client correctly."""
        mock_client_instance = MagicMock()
        mock_ad_manager.return_value = mock_client_instance

        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        client.get_service("OrderService")

        mock_client_instance.GetService.assert_called_once_with(
            "OrderService", version="v202411"
        )

    @patch("gam_mcp.client.ad_manager.StatementBuilder")
    def test_create_statement(self, mock_statement_builder):
        """Test create_statement creates a StatementBuilder."""
        client = GAMClient(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        client.create_statement()

        mock_statement_builder.assert_called_once_with(version="v202411")


class TestGlobalClient:
    """Tests for global client management functions."""

    def setup_method(self):
        """Reset global client before each test."""
        import gam_mcp.client as client_module
        client_module._gam_client = None

    def test_get_gam_client_raises_without_init(self):
        """Test get_gam_client raises error if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_gam_client()

        assert "GAM client not initialized" in str(exc_info.value)

    @patch("gam_mcp.client.GAMClient")
    def test_init_gam_client_creates_client(self, mock_gam_client_class):
        """Test init_gam_client creates and stores a client."""
        mock_client = MagicMock()
        mock_gam_client_class.return_value = mock_client

        result = init_gam_client(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        mock_gam_client_class.assert_called_once_with(
            "/path/to/creds.json",
            "12345678",
            "GAM MCP Server",
        )
        assert result == mock_client

    @patch("gam_mcp.client.GAMClient")
    def test_get_gam_client_after_init(self, mock_gam_client_class):
        """Test get_gam_client returns client after initialization."""
        mock_client = MagicMock()
        mock_gam_client_class.return_value = mock_client

        init_gam_client(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
        )

        result = get_gam_client()
        assert result == mock_client

    @patch("gam_mcp.client.GAMClient")
    def test_init_gam_client_with_custom_app_name(self, mock_gam_client_class):
        """Test init_gam_client accepts custom application name."""
        init_gam_client(
            credentials_path="/path/to/creds.json",
            network_code="12345678",
            application_name="Custom App",
        )

        mock_gam_client_class.assert_called_once_with(
            "/path/to/creds.json",
            "12345678",
            "Custom App",
        )
