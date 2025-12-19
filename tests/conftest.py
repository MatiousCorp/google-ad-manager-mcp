"""Pytest configuration and fixtures for GAM MCP Server tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_gam_client():
    """Create a mock GAM client for testing."""
    with patch("gam_mcp.client.GAMClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_zeep_object():
    """Create a mock zeep object for testing utility functions."""

    class MockZeepObject:
        """Mock zeep object with __values__ attribute."""

        def __init__(self, data: dict):
            self.__values__ = data
            for key, value in data.items():
                setattr(self, key, value)

        def __getitem__(self, key):
            return self.__values__[key]

    return MockZeepObject


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "id": 123456,
        "name": "Test Campaign 2025",
        "advertiserId": 789,
        "status": "APPROVED",
        "startDateTime": {
            "date": {"year": 2025, "month": 1, "day": 1},
            "hour": 0,
            "minute": 0,
            "second": 0,
        },
        "endDateTime": {
            "date": {"year": 2025, "month": 12, "day": 31},
            "hour": 23,
            "minute": 59,
            "second": 59,
        },
    }


@pytest.fixture
def sample_line_item_data():
    """Sample line item data for testing."""
    return {
        "id": 654321,
        "name": "Display Banner",
        "orderId": 123456,
        "status": "DELIVERING",
        "lineItemType": "STANDARD",
        "primaryGoal": {
            "goalType": "LIFETIME",
            "unitType": "IMPRESSIONS",
            "units": 100000,
        },
        "creativePlaceholders": [
            {"size": {"width": 300, "height": 250}},
            {"size": {"width": 728, "height": 90}},
        ],
    }


@pytest.fixture
def sample_creative_data():
    """Sample creative data for testing."""
    return {
        "id": 111222,
        "name": "banner_300x250.png",
        "advertiserId": 789,
        "size": {"width": 300, "height": 250},
        "previewUrl": "https://example.com/preview",
    }


@pytest.fixture
def sample_advertiser_data():
    """Sample advertiser data for testing."""
    return {
        "id": 789,
        "name": "ACME Corporation",
        "type": "ADVERTISER",
        "creditStatus": "ACTIVE",
    }
