import pytest
from unittest.mock import MagicMock, patch
import logging

# Corrected import path for the function to be tested
from src.components.store_bigquery import store_emails_in_bigquery


# Mock a sample email dictionary for testing
@pytest.fixture
def mock_email():
    return {
        "message_id": "mock_message_id_123",
        "thread_id": "mock_thread_id_456",
        "subject": "Mock Subject",
        "sender": "sender@example.com",
        "recipient": "recipient@example.com",
        "date_received": "Mon, 21 Oct 2024 10:00:00 -0700",
        "parsed_date": "2024-10-21T10:00:00-07:00",
        "body_text": "This is a mock email body.",
        "label_ids": ["INBOX", "UNREAD"],
        "snippet": "This is a snippet.",
        "message_size": 12345,
        "attachment_count": 0,
        "attachments": [],
        "processed_at": "2024-10-21T10:00:00-07:00",
    }


# Mock a sample table reference
@pytest.fixture
def mock_table_ref():
    return MagicMock()


# Mock a BigQuery client for successful operations
@pytest.fixture
def mock_bigquery_client_success():
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []
    return mock_client


# Mock a BigQuery client for failed operations (with errors)
@pytest.fixture
def mock_bigquery_client_failure():
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = [{"index": 0, "errors": "Mock error"}]
    return mock_client


# --- Test Cases ---
def test_store_emails_in_bigquery_success(
    mock_bigquery_client_success, mock_table_ref, mock_email
):
    """Tests a successful email insertion into BigQuery."""
    result = store_emails_in_bigquery(
        mock_bigquery_client_success, mock_table_ref, mock_email
    )

    # Assert that the function returned True
    assert result is True

    # Assert that insert_rows_json was called exactly once with the correct data
    mock_bigquery_client_success.insert_rows_json.assert_called_once()

    # Get the arguments that insert_rows_json was called with
    args, _ = mock_bigquery_client_success.insert_rows_json.call_args

    # Verify the table reference is correct
    assert args[0] == mock_table_ref

    # Verify the data being inserted is a list with one dictionary
    inserted_data = args[1]
    assert isinstance(inserted_data, list)
    assert len(inserted_data) == 1

    # Verify the dictionary content matches the mock email (with some exceptions)
    inserted_row = inserted_data[0]
    for key in mock_email:
        if key == "body_text":
            assert inserted_row[key] == mock_email[key][:1000000]
        elif key == "attachments":
            assert "attachments" not in inserted_row.keys()
        else:
            assert inserted_row[key] == mock_email[key]


def test_store_emails_in_bigquery_no_email():
    """Tests the function's behavior when no email data is provided."""
    mock_client = MagicMock()
    mock_table_ref = MagicMock()

    result = store_emails_in_bigquery(mock_client, mock_table_ref, None)

    assert result is False
    mock_client.insert_rows_json.assert_not_called()


def test_store_emails_in_bigquery_insertion_error(
    mock_bigquery_client_failure, mock_table_ref, mock_email
):
    """Tests the function's behavior when BigQuery returns insertion errors."""
    result = store_emails_in_bigquery(
        mock_bigquery_client_failure, mock_table_ref, mock_email
    )

    assert result is False
    mock_bigquery_client_failure.insert_rows_json.assert_called_once()


def test_store_emails_in_bigquery_exception(mock_table_ref, mock_email):
    """Tests the function's behavior when an unexpected exception occurs."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.side_effect = Exception("A general error occurred")

    result = store_emails_in_bigquery(mock_client, mock_table_ref, mock_email)

    assert result is False
    mock_client.insert_rows_json.assert_called_once()
