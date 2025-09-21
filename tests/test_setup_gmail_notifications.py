import pytest
import datetime
import logging
from unittest.mock import patch, MagicMock

# Functions to be tested
from src.components.setup_gmail_notifications import (
    setup_gmail_push_notifications,
    stop_gmail_push_notifications,
)

# Configure logging for testing
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


# Mock the Gmail API service object
@pytest.fixture
def mock_gmail_service():
    """Mocks the entire Gmail API service chain."""
    mock_service = MagicMock()
    mock_service.users.return_value.watch.return_value.execute.return_value = {
        "historyId": "12345",
        "expiration": "1672531200000",  # Example timestamp in milliseconds
    }
    mock_service.users.return_value.stop.return_value.execute.return_value = None
    return mock_service


# --- Unit Tests ---
def test_setup_gmail_push_notifications_success(mock_gmail_service, caplog):
    """
    Tests successful setup of push notifications.
    Verifies API call and correct return value.
    """
    with patch(
        "src.components.setup_gmail_notifications.PROJECT_ID", "mock-project-dev"
    ), patch(
        "src.components.setup_gmail_notifications.PUBSUB_TOPIC", "email-notifier"
    ), patch(
        "src.components.setup_gmail_notifications.datetime"
    ) as mock_dt:

        with caplog.at_level(logging.INFO):
            # Mock datetime for a consistent expiration date
            mock_dt.datetime.fromtimestamp.return_value = datetime.datetime(
                2023, 1, 1, 0, 0
            )

            # Call the function
            result = setup_gmail_push_notifications(mock_gmail_service)

            # Assertions
            assert result is not None
            assert result["historyId"] == "12345"

            # Verify that the watch method was called with the correct arguments
            mock_gmail_service.users.return_value.watch.assert_called_once_with(
                userId="me",
                body={
                    "topicName": "projects/mock-project-dev/topics/email-notifier",
                    "labelIds": ["INBOX"],
                    "labelFilterAction": "include",
                },
            )
            # Verify a successful log message
            assert "Gmail push notifications set up successfully!" in caplog.text


def test_setup_gmail_push_notifications_api_error(mock_gmail_service, caplog):
    """
    Tests error handling when the Gmail API call fails.
    """
    with patch(
        "src.components.setup_gmail_notifications.PROJECT_ID", "mock-project-dev"
    ), patch("src.components.setup_gmail_notifications.PUBSUB_TOPIC", "email-notifier"):

        with caplog.at_level(logging.ERROR):
            # Configure the mock to raise an exception
            mock_gmail_service.users.return_value.watch.return_value.execute.side_effect = Exception(
                "API Error"
            )

            # Call the function
            result = setup_gmail_push_notifications(mock_gmail_service)

            # Assertions
            assert result is None
            # Verify an error log message
            assert "Error setting up push notifications: API Error" in caplog.text


def test_stop_gmail_push_notifications_success(mock_gmail_service, caplog):
    """
    Tests successful stopping of push notifications.
    """
    with caplog.at_level(logging.INFO):
        # Call the function
        result = stop_gmail_push_notifications(mock_gmail_service)

        # Assertions
        assert result is True  # Function should return True on success
        # Verify that the stop method was called correctly
        mock_gmail_service.users.return_value.stop.assert_called_once_with(userId="me")
        # Verify the successful log messages
        assert "Stopping Gmail push notifications for user: me" in caplog.text
        assert "Gmail push notifications stopped successfully!" in caplog.text


def test_stop_gmail_push_notifications_api_error(mock_gmail_service, caplog):
    """
    Tests error handling when stopping push notifications fails.
    """
    with caplog.at_level(logging.ERROR):
        # Configure the mock to raise an exception
        mock_gmail_service.users.return_value.stop.return_value.execute.side_effect = (
            Exception("Stop Error")
        )

        # Call the function
        stop_gmail_push_notifications(mock_gmail_service)

        # Assertions
        # Verify that the API call was attempted
        mock_gmail_service.users.return_value.stop.assert_called_once()
        # Verify an error log message
        assert "Stop Error" in caplog.text
