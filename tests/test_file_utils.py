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
    upload_secret,
    download_secret,
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


class TestUploadSecret:
    """Test cases for upload_secret function."""

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    @patch("builtins.print")
    def test_upload_secret_success(self, mock_print, mock_client_class):
        """Test successful secret upload."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.name = "projects/test-project/secrets/test-secret/versions/1"
        mock_client.add_secret_version.return_value = mock_response

        # Test
        result = upload_secret("test-project", "test-secret", "test-payload")

        # Assertions
        assert result == mock_response
        mock_client.add_secret_version.assert_called_once()
        mock_print.assert_called_with(
            "✅ Added secret version: projects/test-project/secrets/test-secret/versions/1"
        )

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    @patch("builtins.print")
    def test_upload_secret_failure(self, mock_print, mock_client_class):
        """Test failed secret upload."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.add_secret_version.side_effect = Exception("Upload failed")

        # Test
        result = upload_secret("test-project", "test-secret", "test-payload")

        # Assertions
        assert result is None
        mock_print.assert_called_with("❌ Failed to upload secret: Upload failed")

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    def test_upload_secret_correct_parameters(self, mock_client_class):
        """Test that upload_secret calls the API with correct parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_client.add_secret_version.return_value = mock_response

        # Test
        upload_secret("my-project", "my-secret", "my-payload")

        # Verify correct API call
        expected_request = {
            "parent": "projects/my-project/secrets/my-secret",
            "payload": {"data": b"my-payload"},
        }
        mock_client.add_secret_version.assert_called_once_with(request=expected_request)


class TestDownloadSecret:
    """Test cases for download_secret function."""

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    @patch("builtins.print")
    def test_download_secret_success(self, mock_print, mock_client_class, caplog):
        """Test successful secret download."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.payload.data = b"secret-value"
        mock_client.access_secret_version.return_value = mock_response

        with caplog.at_level(logging.INFO):
            # Test
            result = download_secret("test-project", "test-secret")

        # Assertions
        assert result == "secret-value"
        assert "Successfully accessed secret: test-secret" in caplog.text

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    @patch("builtins.print")
    def test_download_secret_failure(self, mock_print, mock_client_class):
        """Test failed secret download."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.access_secret_version.side_effect = Exception("Download failed")

        # Test
        result = download_secret("test-project", "test-secret")

        # Assertions
        assert result is None
        mock_print.assert_called_with("❌ Failed to download secret: Download failed")

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    def test_download_secret_correct_parameters(self, mock_client_class):
        """Test that download_secret calls the API with correct parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.payload.data = b"test-data"
        mock_client.access_secret_version.return_value = mock_response

        # Test
        download_secret("my-project", "my-secret")

        # Verify correct API call
        expected_request = {
            "name": "projects/my-project/secrets/my-secret/versions/latest"
        }
        mock_client.access_secret_version.assert_called_once_with(
            request=expected_request
        )

    @patch("src.utils.file_utils.secretmanager.SecretManagerServiceClient")
    def test_download_secret_unicode_handling(self, mock_client_class):
        """Test that download_secret handles unicode correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Test with unicode content
        unicode_content = "Hello 世界! 🌍"
        mock_response = MagicMock()
        mock_response.payload.data = unicode_content.encode("utf-8")
        mock_client.access_secret_version.return_value = mock_response

        # Test
        result = download_secret("test-project", "test-secret")

        # Should correctly decode unicode
        assert result == unicode_content
