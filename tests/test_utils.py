"""Tests for utility functions."""

from gam_mcp.utils import safe_get, extract_date, zeep_to_dict


class TestSafeGet:
    """Tests for safe_get utility function."""

    def test_safe_get_from_dict(self):
        """Test safe_get with a regular dictionary."""
        data = {"name": "Test", "value": 123}
        assert safe_get(data, "name") == "Test"
        assert safe_get(data, "value") == 123

    def test_safe_get_missing_key_returns_default(self):
        """Test safe_get returns default for missing keys."""
        data = {"name": "Test"}
        assert safe_get(data, "missing") is None
        assert safe_get(data, "missing", "default") == "default"

    def test_safe_get_from_none_returns_default(self):
        """Test safe_get with None object."""
        assert safe_get(None, "key") is None
        assert safe_get(None, "key", "default") == "default"

    def test_safe_get_from_object_with_attribute(self, mock_zeep_object):
        """Test safe_get with an object that has attributes."""
        obj = mock_zeep_object({"name": "Test", "id": 123})
        assert safe_get(obj, "name") == "Test"
        assert safe_get(obj, "id") == 123

    def test_safe_get_with_none_value_in_dict(self):
        """Test safe_get returns None when dict value is explicitly None."""
        # Dict.get returns the stored value (None), not the default
        data = {"name": None}
        assert safe_get(data, "name", "default") is None

    def test_safe_get_with_falsy_values(self):
        """Test safe_get handles falsy values correctly."""
        data = {"zero": 0, "empty": "", "false": False}
        assert safe_get(data, "zero") == 0
        assert safe_get(data, "empty") == ""
        assert safe_get(data, "false") is False

    def test_safe_get_nested_access(self, mock_zeep_object):
        """Test safe_get can access nested structures."""
        inner = mock_zeep_object({"value": 42})
        outer = mock_zeep_object({"inner": inner})
        inner_obj = safe_get(outer, "inner")
        assert safe_get(inner_obj, "value") == 42


class TestExtractDate:
    """Tests for extract_date utility function."""

    def test_extract_date_from_dict(self):
        """Test extracting date from a dictionary structure."""
        datetime_obj = {
            "date": {"year": 2025, "month": 6, "day": 15}
        }
        assert extract_date(datetime_obj) == "2025-06-15"

    def test_extract_date_with_single_digit_month_day(self):
        """Test date formatting pads single digits."""
        datetime_obj = {
            "date": {"year": 2025, "month": 1, "day": 5}
        }
        assert extract_date(datetime_obj) == "2025-01-05"

    def test_extract_date_from_none_returns_none(self):
        """Test extract_date with None returns None."""
        assert extract_date(None) is None

    def test_extract_date_missing_date_returns_none(self):
        """Test extract_date with missing date property."""
        datetime_obj = {"time": "12:00"}
        assert extract_date(datetime_obj) is None

    def test_extract_date_missing_year_returns_none(self):
        """Test extract_date with missing year."""
        datetime_obj = {
            "date": {"month": 6, "day": 15}
        }
        assert extract_date(datetime_obj) is None

    def test_extract_date_defaults_month_and_day(self):
        """Test extract_date uses defaults for missing month/day."""
        datetime_obj = {
            "date": {"year": 2025}
        }
        assert extract_date(datetime_obj) == "2025-01-01"

    def test_extract_date_from_zeep_object(self, mock_zeep_object):
        """Test extracting date from a zeep-like object."""
        date_obj = mock_zeep_object({"year": 2025, "month": 12, "day": 31})
        datetime_obj = mock_zeep_object({"date": date_obj})
        assert extract_date(datetime_obj) == "2025-12-31"


class TestZeepToDict:
    """Tests for zeep_to_dict utility function."""

    def test_zeep_to_dict_with_none(self):
        """Test zeep_to_dict with None returns None."""
        assert zeep_to_dict(None) is None

    def test_zeep_to_dict_with_primitives(self):
        """Test zeep_to_dict passes through primitive types."""
        assert zeep_to_dict("string") == "string"
        assert zeep_to_dict(123) == 123
        assert zeep_to_dict(3.14) == 3.14
        assert zeep_to_dict(True) is True
        assert zeep_to_dict(False) is False

    def test_zeep_to_dict_with_list(self):
        """Test zeep_to_dict converts lists recursively."""
        result = zeep_to_dict([1, 2, 3])
        assert result == [1, 2, 3]

    def test_zeep_to_dict_with_nested_list(self, mock_zeep_object):
        """Test zeep_to_dict converts nested lists with objects."""
        obj1 = mock_zeep_object({"id": 1})
        obj2 = mock_zeep_object({"id": 2})
        result = zeep_to_dict([obj1, obj2])
        assert result == [{"id": 1}, {"id": 2}]

    def test_zeep_to_dict_with_dict(self):
        """Test zeep_to_dict passes through regular dicts."""
        data = {"key": "value", "nested": {"inner": 123}}
        result = zeep_to_dict(data)
        assert result == {"key": "value", "nested": {"inner": 123}}

    def test_zeep_to_dict_with_zeep_object(self, mock_zeep_object):
        """Test zeep_to_dict converts zeep objects to dicts."""
        obj = mock_zeep_object({
            "id": 123,
            "name": "Test",
            "active": True,
        })
        result = zeep_to_dict(obj)
        assert result == {"id": 123, "name": "Test", "active": True}

    def test_zeep_to_dict_with_nested_zeep_objects(self, mock_zeep_object):
        """Test zeep_to_dict handles nested zeep objects."""
        inner = mock_zeep_object({"value": 42})
        outer = mock_zeep_object({"id": 1, "inner": inner})
        result = zeep_to_dict(outer)
        assert result == {"id": 1, "inner": {"value": 42}}

    def test_zeep_to_dict_with_tuple(self):
        """Test zeep_to_dict converts tuples to lists."""
        result = zeep_to_dict((1, 2, 3))
        assert result == [1, 2, 3]

    def test_zeep_to_dict_complex_structure(self, mock_zeep_object):
        """Test zeep_to_dict with complex nested structure."""
        size = mock_zeep_object({"width": 300, "height": 250})
        placeholder = mock_zeep_object({"size": size})
        line_item = mock_zeep_object({
            "id": 123,
            "name": "Banner",
            "creativePlaceholders": [placeholder],
        })
        result = zeep_to_dict(line_item)
        assert result == {
            "id": 123,
            "name": "Banner",
            "creativePlaceholders": [{"size": {"width": 300, "height": 250}}],
        }
