"""Tests for line item tools."""

import pytest
from unittest.mock import patch, MagicMock

from gam_mcp.tools import line_items


class TestGetLineItem:
    """Tests for get_line_item function."""

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when line item doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.get_line_item(line_item_id=999)

        assert "error" in result
        assert "not found" in result["error"]

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_line_item_details(self, mock_get_client):
        """Test successfully returns line item details."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "orderId": 456,
                "status": "DELIVERING",
                "lineItemType": "STANDARD",
                "startDateTime": {"date": {"year": 2025, "month": 1, "day": 1}},
                "endDateTime": {"date": {"year": 2025, "month": 12, "day": 31}},
                "costType": "CPM",
                "creativePlaceholders": [
                    {"size": {"width": 300, "height": 250}}
                ],
                "stats": {"impressionsDelivered": 1000, "clicksDelivered": 10},
                "deliveryRateType": "EVENLY",
                "environmentType": "BROWSER"
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.get_line_item(line_item_id=123)

        assert result["id"] == 123
        assert result["name"] == "Test Line Item"
        assert result["status"] == "DELIVERING"
        assert "300x250" in result["creative_placeholders"]
        assert result["impressions_delivered"] == 1000
        assert result["clicks_delivered"] == 10


class TestCreateLineItem:
    """Tests for create_line_item function."""

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_creates_line_item_successfully(self, mock_get_client):
        """Test successfully creates a line item."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItems.return_value = [{
            "id": 123,
            "name": "New Line Item",
            "orderId": 456,
            "status": "DRAFT",
            "lineItemType": "STANDARD"
        }]
        mock_client.get_service.return_value = mock_service

        result = line_items.create_line_item(
            order_id=456,
            name="New Line Item",
            end_year=2025,
            end_month=12,
            end_day=31,
            target_ad_unit_id="123456"
        )

        assert result["id"] == 123
        assert result["name"] == "New Line Item"
        assert "created successfully" in result["message"]

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_uses_default_creative_placeholders(self, mock_get_client):
        """Test uses default creative sizes when not provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItems.return_value = [{
            "id": 123,
            "name": "New Line Item",
            "orderId": 456,
            "status": "DRAFT",
            "lineItemType": "STANDARD"
        }]
        mock_client.get_service.return_value = mock_service

        line_items.create_line_item(
            order_id=456,
            name="New Line Item",
            end_year=2025,
            end_month=12,
            end_day=31,
            target_ad_unit_id="123456"
        )

        # Verify createLineItems was called with default placeholders
        call_args = mock_service.createLineItems.call_args[0][0][0]
        assert len(call_args["creativePlaceholders"]) == 4

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_uses_custom_creative_sizes(self, mock_get_client):
        """Test uses custom creative sizes when provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItems.return_value = [{
            "id": 123,
            "name": "New Line Item",
            "orderId": 456,
            "status": "DRAFT",
            "lineItemType": "STANDARD"
        }]
        mock_client.get_service.return_value = mock_service

        custom_sizes = [{"width": 970, "height": 250}]
        line_items.create_line_item(
            order_id=456,
            name="New Line Item",
            end_year=2025,
            end_month=12,
            end_day=31,
            target_ad_unit_id="123456",
            creative_sizes=custom_sizes
        )

        call_args = mock_service.createLineItems.call_args[0][0][0]
        assert len(call_args["creativePlaceholders"]) == 1
        assert call_args["creativePlaceholders"][0]["size"]["width"] == 970

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_error_on_creation_failure(self, mock_get_client):
        """Test returns error when creation fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItems.return_value = None
        mock_client.get_service.return_value = mock_service

        result = line_items.create_line_item(
            order_id=456,
            name="New Line Item",
            end_year=2025,
            end_month=12,
            end_day=31,
            target_ad_unit_id="123456"
        )

        assert "error" in result
        assert "Failed to create" in result["error"]


class TestDuplicateLineItem:
    """Tests for duplicate_line_item function."""

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_error_when_source_not_found(self, mock_get_client):
        """Test returns error when source line item doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.duplicate_line_item(
            source_line_item_id=999,
            new_name="Duplicate"
        )

        assert "error" in result

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_duplicates_line_item_successfully(self, mock_get_client):
        """Test successfully duplicates a line item."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Original",
                "orderId": 456,
                "lineItemType": "STANDARD",
                "costType": "CPM",
                "creativePlaceholders": [{"size": {"width": 300, "height": 250}}]
            }]
        }
        mock_service.createLineItems.return_value = [{
            "id": 789,
            "name": "Duplicate",
            "orderId": 456,
            "status": "DRAFT"
        }]
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.duplicate_line_item(
            source_line_item_id=123,
            new_name="Duplicate"
        )

        assert result["new_line_item"]["id"] == 789
        assert result["new_line_item"]["name"] == "Duplicate"
        assert "duplicated successfully" in result["message"]

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_renames_source_when_requested(self, mock_get_client):
        """Test renames source line item when requested."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Original",
                "orderId": 456,
                "lineItemType": "STANDARD",
                "costType": "CPM"
            }]
        }
        mock_service.updateLineItems.return_value = [{
            "id": 123,
            "name": "Renamed Original"
        }]
        mock_service.createLineItems.return_value = [{
            "id": 789,
            "name": "Duplicate",
            "orderId": 456,
            "status": "DRAFT"
        }]
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.duplicate_line_item(
            source_line_item_id=123,
            new_name="Duplicate",
            rename_source="Renamed Original"
        )

        assert result["source_line_item"]["renamed_to"] == "Renamed Original"
        mock_service.updateLineItems.assert_called_once()


class TestUpdateLineItemName:
    """Tests for update_line_item_name function."""

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when line item doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.update_line_item_name(
            line_item_id=999,
            new_name="New Name"
        )

        assert "error" in result

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_updates_name_successfully(self, mock_get_client):
        """Test successfully updates line item name."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{"id": 123, "name": "Old Name"}]
        }
        mock_service.updateLineItems.return_value = [{
            "id": 123,
            "name": "New Name"
        }]
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.update_line_item_name(
            line_item_id=123,
            new_name="New Name"
        )

        assert result["old_name"] == "Old Name"
        assert result["new_name"] == "New Name"
        assert "renamed" in result["message"]


class TestListLineItemsByOrder:
    """Tests for list_line_items_by_order function."""

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_empty_when_no_line_items(self, mock_get_client):
        """Test returns empty list when order has no line items."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.list_line_items_by_order(order_id=123)

        assert result["line_items"] == []
        assert result["total"] == 0

    @patch("gam_mcp.tools.line_items.get_gam_client")
    def test_returns_all_line_items_for_order(self, mock_get_client):
        """Test returns all line items for an order."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [
                {
                    "id": 1,
                    "name": "LI1",
                    "status": "DELIVERING",
                    "lineItemType": "STANDARD",
                    "stats": {"impressionsDelivered": 100, "clicksDelivered": 5}
                },
                {
                    "id": 2,
                    "name": "LI2",
                    "status": "READY",
                    "lineItemType": "SPONSORSHIP",
                    "stats": {"impressionsDelivered": 0, "clicksDelivered": 0}
                }
            ]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = line_items.list_line_items_by_order(order_id=123)

        assert result["total"] == 2
        assert result["line_items"][0]["name"] == "LI1"
        assert result["line_items"][0]["impressions_delivered"] == 100
        assert result["line_items"][1]["name"] == "LI2"
