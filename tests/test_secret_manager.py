import logging
from unittest.mock import patch, MagicMock
from datetime import datetime
from email.utils import formatdate

# Import the functions to test
from src.components.secret_manager import (
    upload_secret,
    download_secret,
)

# Configure logging for testing
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


class TestUploadSecret:
    """Test cases for upload_secret function."""

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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

    @patch("src.components.secret_manager.secretmanager.SecretManagerServiceClient")
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
