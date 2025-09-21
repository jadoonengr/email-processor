import pytest
import json
import logging
from unittest.mock import patch, MagicMock, call
from datetime import datetime

# Import the main function to test
from main import process_emails

# Configure logging for testing
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_cloud_event():
    """Create a mock CloudEvent object."""
    mock_event = MagicMock()
    # Base64 encoded JSON data for Gmail notification
    test_data = json.dumps({"historyId": "12345"})
    mock_event.data = {
        "message": {
            "data": "eyJoaXN0b3J5SWQiOiAiMTIzNDUifQ=="  # base64 encoded {"historyId": "12345"}
        }
    }
    return mock_event


@pytest.fixture
def mock_services():
    """Create mock services for authentication."""
    return {
        "gmail_service": MagicMock(),
        "bigquery_client": MagicMock(),
        "storage_client": MagicMock(),
    }


class TestProcessEmails:
    """Test cases for the main process_emails function."""

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.GCS_BUCKET_NAME", "test-bucket")
    @patch("main.BIGQUERY_DATASET", "test-dataset")
    @patch("main.BIGQUERY_TABLE", "test-table")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.upload_attachment_to_gcs")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_success_with_attachments(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_upload_gcs,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test successful email processing with attachments."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]

        # Mock email data
        mock_emails = [{"id": "email123"}]
        mock_list_emails.return_value = mock_emails

        mock_email_data = {
            "id": "email123",
            "subject": "Test Email",
            "attachments": [
                {
                    "file_name": "test.pdf",
                    "file_data": b"test file data",
                    "file_type": "application/pdf",
                }
            ],
        }
        mock_read_email.return_value = mock_email_data
        mock_upload_gcs.return_value = (
            "https://storage.googleapis.com/test-bucket/test.pdf"
        )

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Assertions
        mock_decode_base64.assert_called_once()
        mock_auth_gmail.assert_called_once()
        mock_auth_bigquery.assert_called_once_with("test-project")
        mock_auth_gcs.assert_called_once_with("test-project")
        mock_setup_notifications.assert_called_once_with(mock_services["gmail_service"])
        mock_list_emails.assert_called_once_with(
            mock_services["gmail_service"], max_results=100
        )
        mock_read_email.assert_called_once_with(
            mock_services["gmail_service"], "email123"
        )
        mock_upload_gcs.assert_called_once_with(
            mock_services["storage_client"],
            "test-bucket",
            "test.pdf",
            b"test file data",
            "application/pdf",
            "email123",
        )
        mock_store_bigquery.assert_called_once_with(
            mock_services["bigquery_client"],
            "test-project.test-dataset.test-table",
            mock_email_data,
        )
        mock_mark_read.assert_called_once_with(
            mock_services["gmail_service"], "email123"
        )

        # Check log messages
        assert "RUNNING CLOUD FUNCTION" in caplog.text
        assert "All services initialized successfully" in caplog.text
        assert "Found 1 unread messages" in caplog.text
        assert "Processing completed successfully" in caplog.text

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.GCS_BUCKET_NAME", "test-bucket")
    @patch("main.BIGQUERY_DATASET", "test-dataset")
    @patch("main.BIGQUERY_TABLE", "test-table")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_no_unread_emails(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test when no unread emails are found."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]
        mock_list_emails.return_value = []  # No emails

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Assertions
        mock_list_emails.assert_called_once()
        mock_read_email.assert_not_called()
        mock_store_bigquery.assert_not_called()
        mock_mark_read.assert_not_called()

        # Check log message
        assert "No unread emails found" in caplog.text

    @patch("main.authenticate_gmail")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gcs")
    @patch("main.decode_base64")
    def test_process_emails_auth_failure(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_cloud_event,
        caplog,
    ):
        """Test when authentication services fail."""

        # Setup mocks - one service fails
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = None  # Failed authentication
        mock_auth_bigquery.return_value = MagicMock()
        mock_auth_gcs.return_value = MagicMock()

        with caplog.at_level(logging.INFO):
            # Call the function
            result = process_emails(mock_cloud_event)

        # Should exit early with warning
        assert "One or more services failed to initialize" in caplog.text

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.GCS_BUCKET_NAME", "test-bucket")
    @patch("main.BIGQUERY_DATASET", "test-dataset")
    @patch("main.BIGQUERY_TABLE", "test-table")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.upload_attachment_to_gcs")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_with_attachment_no_data(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_upload_gcs,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test processing email with attachment that has no data."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]

        mock_emails = [{"id": "email123"}]
        mock_list_emails.return_value = mock_emails

        mock_email_data = {
            "id": "email123",
            "subject": "Test Email",
            "attachments": [
                {
                    "file_name": "empty.pdf",
                    "file_data": None,  # No data
                    "file_type": "application/pdf",
                }
            ],
        }
        mock_read_email.return_value = mock_email_data

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Assertions
        mock_upload_gcs.assert_not_called()  # Should not try to upload
        assert "No data for attachment: empty.pdf" in caplog.text

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.GCS_BUCKET_NAME", "test-bucket")
    @patch("main.BIGQUERY_DATASET", "test-dataset")
    @patch("main.BIGQUERY_TABLE", "test-table")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.upload_attachment_to_gcs")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_upload_failure(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_upload_gcs,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test when GCS upload fails."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]

        mock_emails = [{"id": "email123"}]
        mock_list_emails.return_value = mock_emails

        mock_email_data = {
            "id": "email123",
            "subject": "Test Email",
            "attachments": [
                {
                    "file_name": "test.pdf",
                    "file_data": b"test file data",
                    "file_type": "application/pdf",
                }
            ],
        }
        mock_read_email.return_value = mock_email_data
        mock_upload_gcs.return_value = None  # Upload failed

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Should log failure message
        assert "Failed to upload attachment: test.pdf" in caplog.text

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_multiple_emails(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test processing multiple emails."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]

        # Multiple emails
        mock_emails = [{"id": "email1"}, {"id": "email2"}, {"id": "email3"}]
        mock_list_emails.return_value = mock_emails

        mock_email_data = {
            "subject": "Test Email",
            "attachments": [],  # No attachments for simplicity
        }
        mock_read_email.return_value = mock_email_data

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Should process all emails
        assert mock_read_email.call_count == 3
        assert mock_store_bigquery.call_count == 3
        assert mock_mark_read.call_count == 3

        # Check calls were made with correct email IDs
        mock_read_email.assert_has_calls(
            [
                call(mock_services["gmail_service"], "email1"),
                call(mock_services["gmail_service"], "email2"),
                call(mock_services["gmail_service"], "email3"),
            ]
        )

    @patch("main.decode_base64")
    def test_process_emails_exception_handling(
        self,
        mock_decode_base64,
        mock_cloud_event,
        caplog,
    ):
        """Test exception handling in main function."""

        # Setup mock to raise exception
        mock_decode_base64.side_effect = Exception("Decoding failed")

        with caplog.at_level(logging.ERROR):
            # Call the function
            process_emails(mock_cloud_event)

        # Should log the error
        assert "An unexpected error occurred: Decoding failed" in caplog.text

    @patch("main.PROJECT_ID", "test-project")
    @patch("main.GCS_BUCKET_NAME", "test-bucket")
    @patch("main.BIGQUERY_DATASET", "test-dataset")
    @patch("main.BIGQUERY_TABLE", "test-table")
    @patch("main.mark_email_read")
    @patch("main.store_emails_in_bigquery")
    @patch("main.upload_attachment_to_gcs")
    @patch("main.read_email")
    @patch("main.list_unread_emails")
    @patch("main.setup_gmail_push_notifications")
    @patch("main.authenticate_gcs")
    @patch("main.authenticate_bigquery")
    @patch("main.authenticate_gmail")
    @patch("main.decode_base64")
    def test_process_emails_email_without_attachments(
        self,
        mock_decode_base64,
        mock_auth_gmail,
        mock_auth_bigquery,
        mock_auth_gcs,
        mock_setup_notifications,
        mock_list_emails,
        mock_read_email,
        mock_upload_gcs,
        mock_store_bigquery,
        mock_mark_read,
        mock_cloud_event,
        mock_services,
        caplog,
    ):
        """Test processing email without attachments."""

        # Setup mocks
        mock_decode_base64.return_value = '{"historyId": "12345"}'
        mock_auth_gmail.return_value = mock_services["gmail_service"]
        mock_auth_bigquery.return_value = mock_services["bigquery_client"]
        mock_auth_gcs.return_value = mock_services["storage_client"]

        mock_emails = [{"id": "email123"}]
        mock_list_emails.return_value = mock_emails

        mock_email_data = {
            "id": "email123",
            "subject": "Test Email",
            "attachments": [],  # No attachments
        }
        mock_read_email.return_value = mock_email_data

        with caplog.at_level(logging.INFO):
            # Call the function
            process_emails(mock_cloud_event)

        # Assertions
        mock_upload_gcs.assert_not_called()  # No attachments to upload
        mock_store_bigquery.assert_called_once()
        mock_mark_read.assert_called_once()

        assert "Processing completed successfully" in caplog.text
