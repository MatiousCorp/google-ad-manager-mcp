"""Tests for advertiser tools."""

import pytest
from unittest.mock import patch, MagicMock

from gam_mcp.tools import advertisers


class TestFindAdvertiser:
    """Tests for find_advertiser function."""

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_empty_when_no_match(self, mock_get_client):
        """Test returns empty list when no advertisers match."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.find_advertiser(name="NonExistent")

        assert result["advertisers"] == []
        assert "No advertiser found" in result["message"]

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_matching_advertisers(self, mock_get_client):
        """Test returns all matching advertisers."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {
            "results": [
                {"id": 1, "name": "ACME Corp", "type": "ADVERTISER", "creditStatus": "ACTIVE"},
                {"id": 2, "name": "ACME Inc", "type": "ADVERTISER", "creditStatus": "ACTIVE"}
            ]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.find_advertiser(name="ACME")

        assert result["total"] == 2
        assert len(result["advertisers"]) == 2
        assert result["advertisers"][0]["name"] == "ACME Corp"

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_uses_bind_variable_for_name(self, mock_get_client):
        """Test uses bind variable for safe querying."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {"results": []}
        mock_client.get_service.return_value = mock_service

        mock_statement = MagicMock()
        mock_client.create_statement.return_value = mock_statement

        advertisers.find_advertiser(name="Test'; DROP TABLE--")

        # Verify bind variable was used
        mock_statement.Where.assert_called()
        mock_statement.Where().WithBindVariable.assert_called()


class TestGetAdvertiser:
    """Tests for get_advertiser function."""

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when advertiser doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.get_advertiser(advertiser_id=999)

        assert "error" in result
        assert "not found" in result["error"]

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_advertiser_details(self, mock_get_client):
        """Test returns advertiser details successfully."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "ACME Corp",
                "type": "ADVERTISER",
                "creditStatus": "ACTIVE",
                "email": "contact@acme.com",
                "address": "123 Main St"
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.get_advertiser(advertiser_id=123)

        assert result["id"] == 123
        assert result["name"] == "ACME Corp"
        assert result["email"] == "contact@acme.com"


class TestListAdvertisers:
    """Tests for list_advertisers function."""

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_empty_when_no_advertisers(self, mock_get_client):
        """Test returns empty list when no advertisers exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.list_advertisers()

        assert result["advertisers"] == []
        assert result["total"] == 0

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_all_advertisers(self, mock_get_client):
        """Test returns all advertisers with limit."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {
            "results": [
                {"id": 1, "name": "Advertiser 1", "creditStatus": "ACTIVE"},
                {"id": 2, "name": "Advertiser 2", "creditStatus": "INACTIVE"}
            ]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.list_advertisers(limit=50)

        assert result["total"] == 2
        assert len(result["advertisers"]) == 2

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_filters_by_advertiser_type(self, mock_get_client):
        """Test only returns companies of type ADVERTISER."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {"results": []}
        mock_client.get_service.return_value = mock_service

        mock_statement = MagicMock()
        mock_client.create_statement.return_value = mock_statement

        advertisers.list_advertisers()

        # Verify type filter was applied
        mock_statement.Where.assert_called_with("type = :type")


class TestCreateAdvertiser:
    """Tests for create_advertiser function."""

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_creates_advertiser_successfully(self, mock_get_client):
        """Test successfully creates an advertiser."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCompanies.return_value = [{
            "id": 123,
            "name": "New Advertiser",
            "type": "ADVERTISER"
        }]
        mock_client.get_service.return_value = mock_service

        result = advertisers.create_advertiser(name="New Advertiser")

        assert result["id"] == 123
        assert result["name"] == "New Advertiser"
        assert "created successfully" in result["message"]

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_creates_with_optional_fields(self, mock_get_client):
        """Test creates advertiser with optional fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCompanies.return_value = [{
            "id": 123,
            "name": "New Advertiser",
            "type": "ADVERTISER"
        }]
        mock_client.get_service.return_value = mock_service

        advertisers.create_advertiser(
            name="New Advertiser",
            email="contact@example.com",
            address="123 Main St",
            comment="Test comment"
        )

        call_args = mock_service.createCompanies.call_args[0][0][0]
        assert call_args["email"] == "contact@example.com"
        assert call_args["address"] == "123 Main St"
        assert call_args["comment"] == "Test comment"

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_error_on_creation_failure(self, mock_get_client):
        """Test returns error when creation fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCompanies.return_value = None
        mock_client.get_service.return_value = mock_service

        result = advertisers.create_advertiser(name="New Advertiser")

        assert "error" in result
        assert "Failed to create" in result["error"]


class TestFindOrCreateAdvertiser:
    """Tests for find_or_create_advertiser function."""

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_returns_existing_advertiser_when_found(self, mock_get_client):
        """Test returns existing advertiser when it exists."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Existing Advertiser",
                "type": "ADVERTISER"
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = advertisers.find_or_create_advertiser(name="Existing Advertiser")

        assert result["id"] == 123
        assert result["created"] is False
        assert "Found existing" in result["message"]

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    @patch("gam_mcp.tools.advertisers.create_advertiser")
    def test_creates_new_advertiser_when_not_found(self, mock_create, mock_get_client):
        """Test creates new advertiser when not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {"results": []}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        mock_create.return_value = {
            "id": 123,
            "name": "New Advertiser",
            "type": "ADVERTISER"
        }

        result = advertisers.find_or_create_advertiser(name="New Advertiser")

        assert result["created"] is True
        mock_create.assert_called_once_with(name="New Advertiser", email=None)

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    @patch("gam_mcp.tools.advertisers.create_advertiser")
    def test_passes_email_to_create(self, mock_create, mock_get_client):
        """Test passes email to create when not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {"results": []}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        mock_create.return_value = {"id": 123, "name": "New Advertiser"}

        advertisers.find_or_create_advertiser(
            name="New Advertiser",
            email="contact@example.com"
        )

        mock_create.assert_called_once_with(
            name="New Advertiser",
            email="contact@example.com"
        )

    @patch("gam_mcp.tools.advertisers.get_gam_client")
    def test_uses_exact_name_match(self, mock_get_client):
        """Test uses exact name match, not partial."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCompaniesByStatement.return_value = {"results": []}
        mock_service.createCompanies.return_value = [{"id": 1, "name": "Test", "type": "ADVERTISER"}]
        mock_client.get_service.return_value = mock_service

        mock_statement = MagicMock()
        mock_client.create_statement.return_value = mock_statement

        advertisers.find_or_create_advertiser(name="Exact Name")

        # Verify exact match query (= not LIKE)
        mock_statement.Where.assert_called_with("name = :name AND type = :type")
