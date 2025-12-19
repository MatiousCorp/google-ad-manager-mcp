"""Tests for verification tools."""

import pytest
from unittest.mock import patch, MagicMock

from gam_mcp.tools import verification


class TestVerifyLineItemSetup:
    """Tests for verify_line_item_setup function."""

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when line item doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_line_item_setup(line_item_id=999)

        assert "error" in result

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_returns_ok_status_when_no_issues(self, mock_get_client):
        """Test returns OK status when no issues found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_line_item_service = MagicMock()
        mock_lica_service = MagicMock()
        mock_creative_service = MagicMock()

        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "READY",
                "orderId": 456,
                "creativePlaceholders": [
                    {"size": {"width": 300, "height": 250}}
                ]
            }]
        }

        mock_lica_service.getLineItemCreativeAssociationsByStatement.return_value = {
            "results": [{
                "creativeId": 789,
                "lineItemId": 123,
                "status": "ACTIVE"
            }]
        }

        mock_creative_service.getCreativesByStatement.return_value = {
            "results": [{
                "id": 789,
                "name": "Banner",
                "size": {"width": 300, "height": 250}
            }]
        }

        def get_service(name):
            if name == "LineItemService":
                return mock_line_item_service
            elif name == "LineItemCreativeAssociationService":
                return mock_lica_service
            return mock_creative_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_line_item_setup(line_item_id=123)

        assert result["status"] == "OK"
        assert len(result["issues"]) == 0

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_detects_size_mismatch(self, mock_get_client):
        """Test detects when creative size doesn't match placeholder."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_line_item_service = MagicMock()
        mock_lica_service = MagicMock()
        mock_creative_service = MagicMock()

        # Line item expects 300x250
        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "READY",
                "orderId": 456,
                "creativePlaceholders": [
                    {"size": {"width": 300, "height": 250}}
                ]
            }]
        }

        mock_lica_service.getLineItemCreativeAssociationsByStatement.return_value = {
            "results": [{
                "creativeId": 789,
                "lineItemId": 123,
                "status": "ACTIVE"
            }]
        }

        # Creative is 728x90 - mismatch!
        mock_creative_service.getCreativesByStatement.return_value = {
            "results": [{
                "id": 789,
                "name": "Banner",
                "size": {"width": 728, "height": 90}
            }]
        }

        def get_service(name):
            if name == "LineItemService":
                return mock_line_item_service
            elif name == "LineItemCreativeAssociationService":
                return mock_lica_service
            return mock_creative_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_line_item_setup(line_item_id=123)

        assert result["status"] == "ISSUES_FOUND"
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "SIZE_MISMATCH"

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_detects_no_creatives(self, mock_get_client):
        """Test detects when line item has no creative associations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_line_item_service = MagicMock()
        mock_lica_service = MagicMock()
        mock_creative_service = MagicMock()

        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "READY",
                "orderId": 456,
                "creativePlaceholders": [
                    {"size": {"width": 300, "height": 250}}
                ]
            }]
        }

        # No creative associations
        mock_lica_service.getLineItemCreativeAssociationsByStatement.return_value = {}

        def get_service(name):
            if name == "LineItemService":
                return mock_line_item_service
            elif name == "LineItemCreativeAssociationService":
                return mock_lica_service
            return mock_creative_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_line_item_setup(line_item_id=123)

        assert result["status"] == "NO_CREATIVES"
        assert any(i["type"] == "NO_CREATIVES" for i in result["issues"])

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_accepts_size_override(self, mock_get_client):
        """Test accepts creative with size override matching placeholder."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_line_item_service = MagicMock()
        mock_lica_service = MagicMock()
        mock_creative_service = MagicMock()

        # Line item expects 1000x250
        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "READY",
                "orderId": 456,
                "creativePlaceholders": [
                    {"size": {"width": 1000, "height": 250}}
                ]
            }]
        }

        # LICA has size override to 1000x250
        mock_lica_service.getLineItemCreativeAssociationsByStatement.return_value = {
            "results": [{
                "creativeId": 789,
                "lineItemId": 123,
                "status": "ACTIVE",
                "sizes": [{"width": 1000, "height": 250}]
            }]
        }

        # Creative is 970x250 but with size override
        mock_creative_service.getCreativesByStatement.return_value = {
            "results": [{
                "id": 789,
                "name": "Banner",
                "size": {"width": 970, "height": 250}
            }]
        }

        def get_service(name):
            if name == "LineItemService":
                return mock_line_item_service
            elif name == "LineItemCreativeAssociationService":
                return mock_lica_service
            return mock_creative_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_line_item_setup(line_item_id=123)

        # Should be OK because size override matches placeholder
        assert result["status"] == "OK"
        assert len(result["issues"]) == 0


class TestCheckLineItemDeliveryStatus:
    """Tests for check_line_item_delivery_status function."""

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when line item doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.check_line_item_delivery_status(line_item_id=999)

        assert "error" in result

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_returns_delivery_status(self, mock_get_client):
        """Test returns delivery status with progress."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "DELIVERING",
                "lineItemType": "STANDARD",
                "stats": {
                    "impressionsDelivered": 50000,
                    "clicksDelivered": 250
                },
                "primaryGoal": {
                    "goalType": "LIFETIME",
                    "unitType": "IMPRESSIONS",
                    "units": 100000
                },
                "deliveryRateType": "EVENLY"
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.check_line_item_delivery_status(line_item_id=123)

        assert result["status"] == "DELIVERING"
        assert result["delivery"]["impressions_delivered"] == 50000
        assert result["delivery"]["goal_units"] == 100000
        assert result["delivery"]["progress_percent"] == 50.0

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_handles_zero_goal(self, mock_get_client):
        """Test handles zero goal without division error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getLineItemsByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Line Item",
                "status": "READY",
                "lineItemType": "SPONSORSHIP",
                "stats": {"impressionsDelivered": 0, "clicksDelivered": 0},
                "primaryGoal": {"units": 0}
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.check_line_item_delivery_status(line_item_id=123)

        assert result["delivery"]["progress_percent"] == 0


class TestVerifyOrderSetup:
    """Tests for verify_order_setup function."""

    @patch("gam_mcp.tools.verification.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when order doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getOrdersByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = verification.verify_order_setup(order_id=999)

        assert "error" in result

    @patch("gam_mcp.tools.verification.get_gam_client")
    @patch("gam_mcp.tools.verification.verify_line_item_setup")
    def test_verifies_all_line_items(self, mock_verify_li, mock_get_client):
        """Test verifies all line items in order."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order_service = MagicMock()
        mock_line_item_service = MagicMock()

        mock_order_service.getOrdersByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Test Order",
                "status": "APPROVED",
                "advertiserId": 456
            }]
        }

        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [
                {"id": 1, "name": "LI 1"},
                {"id": 2, "name": "LI 2"}
            ]
        }

        def get_service(name):
            if name == "OrderService":
                return mock_order_service
            return mock_line_item_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        mock_verify_li.return_value = {
            "line_item": {"name": "Test", "status": "READY"},
            "summary": {"creative_count": 2, "issue_count": 0},
            "issues": []
        }

        result = verification.verify_order_setup(order_id=123)

        assert result["order_id"] == 123
        assert len(result["line_items"]) == 2
        assert mock_verify_li.call_count == 2

    @patch("gam_mcp.tools.verification.get_gam_client")
    @patch("gam_mcp.tools.verification.verify_line_item_setup")
    def test_aggregates_issues_from_line_items(self, mock_verify_li, mock_get_client):
        """Test aggregates issues from all line items."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order_service = MagicMock()
        mock_line_item_service = MagicMock()

        mock_order_service.getOrdersByStatement.return_value = {
            "results": [{"id": 123, "name": "Test Order", "status": "APPROVED"}]
        }

        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{"id": 1, "name": "LI 1"}]
        }

        def get_service(name):
            if name == "OrderService":
                return mock_order_service
            return mock_line_item_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        mock_verify_li.return_value = {
            "line_item": {"name": "Test", "status": "READY"},
            "summary": {"creative_count": 0, "issue_count": 1},
            "issues": [{"type": "NO_CREATIVES", "message": "No creatives"}]
        }

        result = verification.verify_order_setup(order_id=123)

        assert result["overall_status"] == "ISSUES_FOUND"
        assert result["summary"]["total_issues"] == 1

    @patch("gam_mcp.tools.verification.get_gam_client")
    @patch("gam_mcp.tools.verification.verify_line_item_setup")
    def test_handles_line_item_verification_error(self, mock_verify_li, mock_get_client):
        """Test handles error from line item verification."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order_service = MagicMock()
        mock_line_item_service = MagicMock()

        mock_order_service.getOrdersByStatement.return_value = {
            "results": [{"id": 123, "name": "Test Order", "status": "APPROVED"}]
        }

        mock_line_item_service.getLineItemsByStatement.return_value = {
            "results": [{"id": 1, "name": "LI 1"}]
        }

        def get_service(name):
            if name == "OrderService":
                return mock_order_service
            return mock_line_item_service

        mock_client.get_service.side_effect = get_service
        mock_client.create_statement.return_value = MagicMock()

        mock_verify_li.return_value = {"error": "Verification failed"}

        result = verification.verify_order_setup(order_id=123)

        assert "error" in result["line_items"][0]
