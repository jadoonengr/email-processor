import pytest
import base64
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime
from email.utils import formatdate

# Import the functions to test
from src.utils.file_utils import (
    decode_base64,
    sanitize_filename,
    parse_email_date,
)

# Configure logging for testing
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


class TestDecodeBase64:
    """Test cases for decode_base64 function."""

    def test_decode_base64_with_proper_padding(self):
        """Test decoding base64 with proper padding."""
        # Create test data
        test_string = "Hello, World!"
        encoded = base64.urlsafe_b64encode(test_string.encode("utf-8")).decode("ascii")

        # Test decoding
        result = decode_base64(encoded)
        assert result == test_string

    def test_decode_base64_without_padding(self):
        """Test decoding base64 without proper padding."""
        # Create test data without padding
        test_string = "Test"
        encoded = base64.urlsafe_b64encode(test_string.encode("utf-8")).decode("ascii")
        # Remove padding
        encoded = encoded.rstrip("=")

        # Test decoding
        result = decode_base64(encoded)
        assert result == test_string

    def test_decode_base64_empty_string(self):
        """Test decoding empty base64 string."""
        result = decode_base64("")
        assert result == ""

    def test_decode_base64_special_characters(self):
        """Test decoding base64 with special characters."""
        test_string = "Special chars: àáâãäå æç èéêë"
        encoded = base64.urlsafe_b64encode(test_string.encode("utf-8")).decode("ascii")

        result = decode_base64(encoded)
        assert result == test_string


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    def test_sanitize_filename_normal(self):
        """Test sanitizing a normal filename."""
        filename = "document.pdf"
        result = sanitize_filename(filename)
        assert result == "document.pdf"

    def test_sanitize_filename_with_unsafe_chars(self):
        """Test sanitizing filename with unsafe characters."""
        filename = 'file<>:"/\\|?*name.txt'
        result = sanitize_filename(filename)
        assert result == "file_________name.txt"

    def test_sanitize_filename_empty(self):
        """Test sanitizing empty filename."""
        result = sanitize_filename("")
        assert result == "unnamed_attachment"

    def test_sanitize_filename_none(self):
        """Test sanitizing None filename."""
        result = sanitize_filename(None)
        assert result == "unnamed_attachment"

    def test_sanitize_filename_too_long(self):
        """Test sanitizing filename that's too long."""
        long_name = "a" * 250  # Very long filename
        extension = ".txt"
        filename = long_name + extension

        result = sanitize_filename(filename)

        # Should be truncated to 200 characters total
        assert len(result) <= 200
        assert result.endswith(".txt")

    def test_sanitize_filename_long_without_extension(self):
        """Test sanitizing long filename without extension."""
        long_name = "a" * 250

        result = sanitize_filename(long_name)

        # Should be truncated to 200 characters
        assert len(result) <= 200
        assert result == "a" * 200


class TestParseEmailDate:
    """Test cases for parse_email_date function."""

    def test_parse_email_date_valid(self):
        """Test parsing valid email date."""
        # RFC 2822 format
        date_str = "Thu, 01 Jan 2023 12:00:00 +0000"
        result = parse_email_date(date_str)

        # Should return ISO format
        assert result.startswith("2023-01-01T12:00:00")

    def test_parse_email_date_different_format(self):
        """Test parsing email date in different valid format."""
        date_str = "1 Jan 2023 12:00:00 GMT"
        result = parse_email_date(date_str)

        assert result.startswith("2023-01-01T12:00:00")

    def test_parse_email_date_invalid(self):
        """Test parsing invalid email date."""
        date_str = "invalid date string"

        # Should return current datetime in ISO format
        result = parse_email_date(date_str)

        # Should be current year (approximately)
        current_year = datetime.now().year
        assert str(current_year) in result

    def test_parse_email_date_empty(self):
        """Test parsing empty date string."""
        result = parse_email_date("")

        # Should return current datetime
        current_year = datetime.now().year
        assert str(current_year) in result
