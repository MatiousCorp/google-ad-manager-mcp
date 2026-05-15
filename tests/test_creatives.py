"""Tests for creative tools."""

import base64
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from gam_mcp.tools import creatives


class TestExtractSizeFromFilename:
    """Tests for extract_size_from_filename function."""

    def test_extracts_size_from_standard_format(self):
        """Test extracts size from standard filename format."""
        width, height = creatives.extract_size_from_filename("banner_300x250.png")
        assert width == 300
        assert height == 250

    def test_extracts_size_from_middle_of_filename(self):
        """Test extracts size from middle of filename."""
        width, height = creatives.extract_size_from_filename("campaign_728x90_v2.jpg")
        assert width == 728
        assert height == 90

    def test_extracts_size_from_start_of_filename(self):
        """Test extracts size from start of filename."""
        width, height = creatives.extract_size_from_filename("1000x250_header.png")
        assert width == 1000
        assert height == 250

    def test_returns_none_when_no_size_found(self):
        """Test returns None when no size pattern found."""
        width, height = creatives.extract_size_from_filename("banner.png")
        assert width is None
        assert height is None

    def test_extracts_first_size_when_multiple_present(self):
        """Test extracts first size when multiple patterns present."""
        width, height = creatives.extract_size_from_filename("300x250_to_728x90.png")
        assert width == 300
        assert height == 250


class TestUploadCreative:
    """Tests for upload_creative function."""

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_file_not_found(self, mock_path_class, mock_get_client):
        """Test returns error when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        result = creatives.upload_creative(
            file_path="/path/to/missing.png",
            advertiser_id=123,
            click_through_url="https://example.com"
        )

        assert "error" in result
        assert "not found" in result["error"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_size_not_in_filename(self, mock_path_class, mock_get_client):
        """Test returns error when size cannot be extracted from filename."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "banner.png"
        mock_path_class.return_value = mock_path

        result = creatives.upload_creative(
            file_path="/path/to/banner.png",
            advertiser_id=123,
            click_through_url="https://example.com"
        )

        assert "error" in result
        assert "Could not extract size" in result["error"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake image data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_uploads_creative_successfully(self, mock_path_class, mock_file, mock_get_client):
        """Test successfully uploads a creative."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "banner_300x250.png"
        mock_path.stem = "banner_300x250"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = [{
            "id": 123,
            "name": "Creative - 300x250 - banner_300x250"
        }]
        mock_client.get_service.return_value = mock_service

        result = creatives.upload_creative(
            file_path="/path/to/banner_300x250.png",
            advertiser_id=456,
            click_through_url="https://example.com"
        )

        assert result["id"] == 123
        assert result["size"] == "300x250"
        assert "uploaded successfully" in result["message"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake image data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_uses_size_override(self, mock_path_class, mock_file, mock_get_client):
        """Test uses size override when provided."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "banner_970x250.png"
        mock_path.stem = "banner_970x250"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = [{
            "id": 123,
            "name": "Creative - 1000x250 - banner_970x250"
        }]
        mock_client.get_service.return_value = mock_service

        result = creatives.upload_creative(
            file_path="/path/to/banner_970x250.png",
            advertiser_id=456,
            click_through_url="https://example.com",
            override_size_width=1000,
            override_size_height=250
        )

        assert result["size"] == "1000x250"
        assert result["original_size"] == "970x250"
        assert result["override_size"] is True


class TestUploadHtml5Creative:
    """Tests for upload_html5_creative function."""

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_file_not_found(self, mock_path_class, mock_get_client):
        """Test returns error when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        result = creatives.upload_html5_creative(
            file_path="/path/to/missing.zip",
            advertiser_id=123,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert "error" in result
        assert "not found" in result["error"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_not_zip(self, mock_path_class, mock_get_client):
        """Test returns error when file is not a .zip."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "bundle.tar"
        mock_path.suffix = ".tar"
        mock_path_class.return_value = mock_path

        result = creatives.upload_html5_creative(
            file_path="/path/to/bundle.tar",
            advertiser_id=123,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert "error" in result
        assert ".zip" in result["error"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake zip data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_uploads_html5_creative_successfully(self, mock_path_class, mock_file, mock_get_client):
        """Test successfully uploads an HTML5 creative."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "interstitial.zip"
        mock_path.stem = "interstitial"
        mock_path.suffix = ".zip"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = [{
            "id": 789,
            "name": "HTML5 Creative - 320x480 - interstitial"
        }]
        mock_client.get_service.return_value = mock_service

        result = creatives.upload_html5_creative(
            file_path="/path/to/interstitial.zip",
            advertiser_id=456,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert result["id"] == 789
        assert result["size"] == "320x480"
        assert result["type"] == "Html5Creative"
        assert result["is_safe_frame_compatible"] is True
        assert "uploaded successfully" in result["message"]

        payload = mock_service.createCreatives.call_args[0][0][0]
        assert payload["xsi_type"] == "Html5Creative"
        assert payload["html5Asset"]["fileName"] == "interstitial.zip"
        assert payload["html5Asset"]["assetByteArray"] == base64.b64encode(b"fake zip data").decode("utf-8")
        assert payload["size"] == {"width": 320, "height": 480, "isAspectRatio": False}
        assert payload["destinationUrl"] == "https://example.com"
        assert payload["isSafeFrameCompatible"] is True

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake zip data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_uses_custom_creative_name(self, mock_path_class, mock_file, mock_get_client):
        """Test user-supplied creative_name is passed through to the payload."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "bundle.zip"
        mock_path.stem = "bundle"
        mock_path.suffix = ".zip"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = [{"id": 1, "name": "My Custom HTML5"}]
        mock_client.get_service.return_value = mock_service

        creatives.upload_html5_creative(
            file_path="/path/to/bundle.zip",
            advertiser_id=1,
            click_through_url="https://example.com",
            width=300,
            height=250,
            creative_name="My Custom HTML5"
        )

        payload = mock_service.createCreatives.call_args[0][0][0]
        assert payload["name"] == "My Custom HTML5"

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake zip data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_respects_safe_frame_compatible_false(self, mock_path_class, mock_file, mock_get_client):
        """Test is_safe_frame_compatible=False flows through to the payload and result."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "bundle.zip"
        mock_path.stem = "bundle"
        mock_path.suffix = ".zip"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = [{"id": 2, "name": "n"}]
        mock_client.get_service.return_value = mock_service

        result = creatives.upload_html5_creative(
            file_path="/path/to/bundle.zip",
            advertiser_id=1,
            click_through_url="https://example.com",
            width=300,
            height=250,
            is_safe_frame_compatible=False
        )

        payload = mock_service.createCreatives.call_args[0][0][0]
        assert payload["isSafeFrameCompatible"] is False
        assert result["is_safe_frame_compatible"] is False

    @patch("gam_mcp.tools.creatives.get_gam_client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake zip data")
    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_create_fails(self, mock_path_class, mock_file, mock_get_client):
        """Test returns error when createCreatives returns empty."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "bundle.zip"
        mock_path.stem = "bundle"
        mock_path.suffix = ".zip"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createCreatives.return_value = []
        mock_client.get_service.return_value = mock_service

        result = creatives.upload_html5_creative(
            file_path="/path/to/bundle.zip",
            advertiser_id=456,
            click_through_url="https://example.com",
            width=300,
            height=250
        )

        assert "error" in result
        assert "Failed to create HTML5 creative" in result["error"]


class TestUploadAndAssociateHtml5Creative:
    """Tests for upload_and_associate_html5_creative function."""

    @patch("gam_mcp.tools.creatives.associate_creative_with_line_item")
    @patch("gam_mcp.tools.creatives.upload_html5_creative")
    def test_uploads_and_associates_successfully(self, mock_upload, mock_associate):
        """Test successfully uploads and associates HTML5 creative."""
        mock_upload.return_value = {
            "id": 789,
            "name": "HTML5 Creative - 320x480",
            "size": "320x480",
            "type": "Html5Creative"
        }
        mock_associate.return_value = {
            "creative_id": 789,
            "line_item_id": 456,
            "message": "associated"
        }

        result = creatives.upload_and_associate_html5_creative(
            file_path="/path/to/interstitial.zip",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert result["creative_id"] == 789
        assert result["line_item_id"] == 456
        assert result["advertiser_id"] == 123
        assert result["type"] == "Html5Creative"
        assert "uploaded and associated" in result["message"]

    @patch("gam_mcp.tools.creatives.upload_html5_creative")
    def test_returns_upload_error(self, mock_upload):
        """Test returns error when upload fails."""
        mock_upload.return_value = {"error": "Upload failed"}

        result = creatives.upload_and_associate_html5_creative(
            file_path="/path/to/bundle.zip",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert "error" in result

    @patch("gam_mcp.tools.creatives.associate_creative_with_line_item")
    @patch("gam_mcp.tools.creatives.upload_html5_creative")
    def test_returns_association_error(self, mock_upload, mock_associate):
        """Test returns error when association fails."""
        mock_upload.return_value = {
            "id": 789,
            "name": "HTML5 Creative",
            "size": "320x480",
            "type": "Html5Creative"
        }
        mock_associate.return_value = {"error": "Association failed"}

        result = creatives.upload_and_associate_html5_creative(
            file_path="/path/to/bundle.zip",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com",
            width=320,
            height=480
        )

        assert "association_error" in result


class TestAssociateCreativeWithLineItem:
    """Tests for associate_creative_with_line_item function."""

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_associates_creative_successfully(self, mock_get_client):
        """Test successfully associates creative with line item."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItemCreativeAssociations.return_value = [{}]
        mock_client.get_service.return_value = mock_service

        result = creatives.associate_creative_with_line_item(
            creative_id=123,
            line_item_id=456
        )

        assert result["creative_id"] == 123
        assert result["line_item_id"] == 456
        assert "associated" in result["message"]

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_uses_size_override(self, mock_get_client):
        """Test uses size override when provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItemCreativeAssociations.return_value = [{}]
        mock_client.get_service.return_value = mock_service

        result = creatives.associate_creative_with_line_item(
            creative_id=123,
            line_item_id=456,
            size_override_width=1000,
            size_override_height=250
        )

        assert result["size_override"] == "1000x250"

        # Verify the LICA was created with size override
        call_args = mock_service.createLineItemCreativeAssociations.call_args[0][0][0]
        assert call_args["sizes"][0]["width"] == 1000
        assert call_args["sizes"][0]["height"] == 250

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_returns_error_on_failure(self, mock_get_client):
        """Test returns error when association fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.createLineItemCreativeAssociations.return_value = None
        mock_client.get_service.return_value = mock_service

        result = creatives.associate_creative_with_line_item(
            creative_id=123,
            line_item_id=456
        )

        assert "error" in result


class TestUploadAndAssociateCreative:
    """Tests for upload_and_associate_creative function."""

    @patch("gam_mcp.tools.creatives.associate_creative_with_line_item")
    @patch("gam_mcp.tools.creatives.upload_creative")
    def test_uploads_and_associates_successfully(self, mock_upload, mock_associate):
        """Test successfully uploads and associates creative."""
        mock_upload.return_value = {
            "id": 123,
            "name": "Creative - 300x250",
            "size": "300x250"
        }
        mock_associate.return_value = {
            "creative_id": 123,
            "line_item_id": 456,
            "message": "associated"
        }

        result = creatives.upload_and_associate_creative(
            file_path="/path/to/banner_300x250.png",
            advertiser_id=789,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert result["creative_id"] == 123
        assert result["line_item_id"] == 456
        assert "uploaded and associated" in result["message"]

    @patch("gam_mcp.tools.creatives.upload_creative")
    def test_returns_upload_error(self, mock_upload):
        """Test returns error when upload fails."""
        mock_upload.return_value = {"error": "Upload failed"}

        result = creatives.upload_and_associate_creative(
            file_path="/path/to/banner_300x250.png",
            advertiser_id=789,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert "error" in result

    @patch("gam_mcp.tools.creatives.associate_creative_with_line_item")
    @patch("gam_mcp.tools.creatives.upload_creative")
    def test_returns_association_error(self, mock_upload, mock_associate):
        """Test returns error when association fails."""
        mock_upload.return_value = {
            "id": 123,
            "name": "Creative",
            "size": "300x250"
        }
        mock_associate.return_value = {"error": "Association failed"}

        result = creatives.upload_and_associate_creative(
            file_path="/path/to/banner_300x250.png",
            advertiser_id=789,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert "association_error" in result


class TestBulkUploadCreatives:
    """Tests for bulk_upload_creatives function."""

    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_folder_not_found(self, mock_path_class):
        """Test returns error when folder doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        result = creatives.bulk_upload_creatives(
            folder_path="/missing/folder",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert "error" in result
        assert "not found" in result["error"]

    @patch("gam_mcp.tools.creatives.Path")
    def test_returns_error_when_no_images_found(self, mock_path_class):
        """Test returns error when folder has no images."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = []
        mock_path_class.return_value = mock_path

        result = creatives.bulk_upload_creatives(
            folder_path="/empty/folder",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert "error" in result
        assert "No image files" in result["error"]

    @patch("gam_mcp.tools.creatives.upload_and_associate_creative")
    @patch("gam_mcp.tools.creatives.Path")
    def test_uploads_all_images_successfully(self, mock_path_class, mock_upload_assoc):
        """Test uploads all images from folder."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        # Create mock files with proper Path behavior for sorting
        mock_file1 = MagicMock(spec=Path)
        mock_file1.name = "banner_300x250.png"
        mock_file1.__str__ = lambda x: "/images/banner_300x250.png"
        mock_file1.__lt__ = lambda self, other: str(self) < str(other)

        mock_file2 = MagicMock(spec=Path)
        mock_file2.name = "banner_728x90.png"
        mock_file2.__str__ = lambda x: "/images/banner_728x90.png"
        mock_file2.__lt__ = lambda self, other: str(self) < str(other)

        # Only return files for lowercase pattern to avoid duplicates
        def mock_glob(pattern):
            if pattern == "*.png":
                return [mock_file1, mock_file2]
            return []

        mock_path.glob.side_effect = mock_glob
        mock_path_class.return_value = mock_path

        mock_upload_assoc.return_value = {
            "creative_id": 123,
            "size": "300x250",
            "message": "success"
        }

        result = creatives.bulk_upload_creatives(
            folder_path="/images",
            advertiser_id=123,
            line_item_id=456,
            click_through_url="https://example.com"
        )

        assert result["success_count"] == 2
        assert result["fail_count"] == 0


class TestGetCreative:
    """Tests for get_creative function."""

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_returns_error_when_not_found(self, mock_get_client):
        """Test returns error when creative doesn't exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCreativesByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = creatives.get_creative(creative_id=999)

        assert "error" in result

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_returns_creative_details(self, mock_get_client):
        """Test returns creative details successfully."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCreativesByStatement.return_value = {
            "results": [{
                "id": 123,
                "name": "Banner Creative",
                "advertiserId": 456,
                "size": {"width": 300, "height": 250},
                "destinationUrl": "https://example.com"
            }]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = creatives.get_creative(creative_id=123)

        assert result["id"] == 123
        assert result["name"] == "Banner Creative"
        assert result["size"] == "300x250"


class TestListCreativesByAdvertiser:
    """Tests for list_creatives_by_advertiser function."""

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_returns_empty_when_no_creatives(self, mock_get_client):
        """Test returns empty list when no creatives exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCreativesByStatement.return_value = {}
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = creatives.list_creatives_by_advertiser(advertiser_id=123)

        assert result["creatives"] == []
        assert result["total"] == 0

    @patch("gam_mcp.tools.creatives.get_gam_client")
    def test_returns_creatives_for_advertiser(self, mock_get_client):
        """Test returns all creatives for advertiser."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_service = MagicMock()
        mock_service.getCreativesByStatement.return_value = {
            "results": [
                {"id": 1, "name": "Creative 1", "size": {"width": 300, "height": 250}},
                {"id": 2, "name": "Creative 2", "size": {"width": 728, "height": 90}}
            ]
        }
        mock_client.get_service.return_value = mock_service
        mock_client.create_statement.return_value = MagicMock()

        result = creatives.list_creatives_by_advertiser(advertiser_id=123)

        assert result["total"] == 2
        assert result["creatives"][0]["size"] == "300x250"
        assert result["creatives"][1]["size"] == "728x90"
