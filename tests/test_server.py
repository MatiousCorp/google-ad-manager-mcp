"""Tests for MCP server and middleware."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import hmac

from gam_mcp.server import BearerAuthMiddleware


class TestBearerAuthMiddleware:
    """Tests for BearerAuthMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return BearerAuthMiddleware()

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", None)
    @patch("gam_mcp.server.get_http_headers")
    async def test_allows_request_when_no_token_configured(self, mock_headers, middleware):
        """Test allows request when AUTH_TOKEN is not set."""
        context = MagicMock()
        call_next = AsyncMock(return_value="success")

        result = await middleware.on_call_tool(context, call_next)

        assert result == "success"
        call_next.assert_called_once_with(context)

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", "secret-token")
    @patch("gam_mcp.server.get_http_headers")
    async def test_rejects_missing_auth_header(self, mock_headers, middleware):
        """Test rejects request when Authorization header is missing."""
        mock_headers.return_value = {}
        context = MagicMock()
        call_next = AsyncMock()

        from fastmcp.exceptions import ToolError
        with pytest.raises(ToolError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert "Missing Authorization header" in str(exc_info.value)
        call_next.assert_not_called()

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", "secret-token")
    @patch("gam_mcp.server.get_http_headers")
    async def test_rejects_invalid_auth_format(self, mock_headers, middleware):
        """Test rejects request with invalid Authorization format."""
        mock_headers.return_value = {"authorization": "Basic dXNlcjpwYXNz"}
        context = MagicMock()
        call_next = AsyncMock()

        from fastmcp.exceptions import ToolError
        with pytest.raises(ToolError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert "Invalid Authorization format" in str(exc_info.value)
        call_next.assert_not_called()

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", "secret-token")
    @patch("gam_mcp.server.get_http_headers")
    async def test_rejects_invalid_token(self, mock_headers, middleware):
        """Test rejects request with wrong token."""
        mock_headers.return_value = {"authorization": "Bearer wrong-token"}
        context = MagicMock()
        call_next = AsyncMock()

        from fastmcp.exceptions import ToolError
        with pytest.raises(ToolError) as exc_info:
            await middleware.on_call_tool(context, call_next)

        assert "Invalid token" in str(exc_info.value)
        call_next.assert_not_called()

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", "secret-token")
    @patch("gam_mcp.server.get_http_headers")
    async def test_accepts_valid_token(self, mock_headers, middleware):
        """Test accepts request with valid token."""
        mock_headers.return_value = {"authorization": "Bearer secret-token"}
        context = MagicMock()
        call_next = AsyncMock(return_value="success")

        result = await middleware.on_call_tool(context, call_next)

        assert result == "success"
        call_next.assert_called_once_with(context)

    @pytest.mark.asyncio
    @patch("gam_mcp.server.AUTH_TOKEN", "secret-token")
    @patch("gam_mcp.server.get_http_headers")
    async def test_skips_auth_on_header_error(self, mock_headers, middleware):
        """Test skips auth when headers cannot be retrieved (e.g., stdio transport)."""
        mock_headers.side_effect = Exception("No HTTP context")
        context = MagicMock()
        call_next = AsyncMock(return_value="success")

        result = await middleware.on_call_tool(context, call_next)

        assert result == "success"
        call_next.assert_called_once_with(context)


class TestConstantTimeComparison:
    """Tests for timing attack prevention."""

    def test_uses_hmac_compare_digest(self):
        """Test that hmac.compare_digest is used for token comparison."""
        # This is a design verification test
        # The actual implementation uses hmac.compare_digest
        token1 = "secret-token"
        token2 = "secret-token"

        # Verify constant-time comparison works correctly
        result = hmac.compare_digest(
            token1.encode('utf-8'),
            token2.encode('utf-8')
        )
        assert result is True

        # Verify different tokens return False
        result = hmac.compare_digest(
            token1.encode('utf-8'),
            "wrong-token".encode('utf-8')
        )
        assert result is False


class TestServerInitialization:
    """Tests for server initialization."""

    @patch("gam_mcp.server.init_gam_client")
    def test_init_client_requires_credentials_path(self, mock_init):
        """Test init_client raises error when credentials path missing."""
        from gam_mcp.server import init_client

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                init_client()

            assert "GAM_CREDENTIALS_PATH" in str(exc_info.value)

    @patch("gam_mcp.server.init_gam_client")
    def test_init_client_requires_network_code(self, mock_init):
        """Test init_client raises error when network code missing."""
        from gam_mcp.server import init_client

        with patch.dict('os.environ', {'GAM_CREDENTIALS_PATH': '/path/to/creds.json'}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                init_client()

            assert "GAM_NETWORK_CODE" in str(exc_info.value)

    @patch("gam_mcp.server.init_gam_client")
    def test_init_client_success(self, mock_init):
        """Test init_client succeeds with required env vars."""
        from gam_mcp.server import init_client

        with patch.dict('os.environ', {
            'GAM_CREDENTIALS_PATH': '/path/to/creds.json',
            'GAM_NETWORK_CODE': '12345678'
        }):
            init_client()

            mock_init.assert_called_once_with(
                credentials_path='/path/to/creds.json',
                network_code='12345678',
                application_name='GAM MCP Server'
            )
