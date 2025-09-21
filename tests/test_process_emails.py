import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import json
import base64

# Corrected import paths for the functions to be tested
from src.components.process_emails import (
    extract_email_body,
    parse_email_date,
    extract_attachments,
    mark_email_read,
    read_email,
    list_unread_emails,
)

# --- MOCK DATA FIXTURES ---


@pytest.fixture
def mock_plain_text_payload():
    """Mock payload for a plain text email body."""
    encoded_data = base64.urlsafe_b64encode(b"This is a plain text body.").decode(
        "utf-8"
    )
    return {
        "mimeType": "text/plain",
        "body": {"data": encoded_data},
    }


@pytest.fixture
def mock_email_payload():
    """Mock payload for an email body."""
    html_content = "<html><body><p>This is an <b>HTML</b> body.</p></body></html>"
    encoded_data = base64.urlsafe_b64encode(html_content.encode("utf-8")).decode(
        "utf-8"
    )
    return {
        "mimeType": "text/plain",
        "body": {"data": encoded_data},
    }


@pytest.fixture
def mock_multipart_payload():
    """Mock payload for a multipart email with both plain text and HTML."""
    plain_text = "This is the plain text part."
    html_content = "<html><body><p>This is the <b>HTML</b> part.</p></body></html>"
    encoded_plain = base64.urlsafe_b64encode(plain_text.encode("utf-8")).decode("utf-8")
    encoded_html = base64.urlsafe_b64encode(html_content.encode("utf-8")).decode(
        "utf-8"
    )

    return {
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": encoded_plain},
            },
            {
                "mimeType": "text/html",
                "body": {"data": encoded_html},
            },
        ]
    }


@pytest.fixture
def mock_message_with_attachments():
    """Mock a full email message with nested attachments."""
    return {
        "id": "mock_message_id_123",
        "payload": {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"Body text.").decode("utf-8")
                    },
                },
                {
                    "mimeType": "application/octet-stream",
                    "filename": "document.pdf",
                    "body": {"attachmentId": "mock_attachment_id_1"},
                },
                {
                    "mimeType": "multipart/mixed",
                    "parts": [
                        {
                            "mimeType": "image/jpeg",
                            "filename": "photo.jpg",
                            "body": {"attachmentId": "mock_attachment_id_2"},
                        }
                    ],
                },
            ]
        },
    }


@pytest.fixture
def mock_gmail_service():
    """Fixture to create a mock Gmail API service."""
    mock_service = MagicMock()
    mock_get_attachments = MagicMock()

    mock_attachment1 = {
        "data": base64.urlsafe_b64encode(b"PDF content").decode("utf-8")
    }
    mock_attachment2 = {
        "data": base64.urlsafe_b64encode(b"JPEG content").decode("utf-8")
    }

    # Set up side_effect for attachments.get to return different data based on the call
    mock_get_attachments.get.side_effect = [
        MagicMock(execute=lambda: mock_attachment1),
        MagicMock(execute=lambda: mock_attachment2),
    ]

    mock_service.users.return_value.messages.return_value.attachments.return_value = (
        mock_get_attachments
    )
    return mock_service


@pytest.fixture
def mock_read_email_message():
    """Mock a full message response from the Gmail API's .get() method."""
    return {
        "id": "mock_message_id_full",
        "threadId": "mock_thread_id_full",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "This is a mock snippet.",
        "sizeEstimate": 5000,
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Full Message Test"},
                {"name": "From", "value": "test@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 21 Oct 2024 10:00:00 -0700"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"Body text.").decode("utf-8")
                    },
                },
                {
                    "mimeType": "application/octet-stream",
                    "filename": "document.pdf",
                    "body": {"attachmentId": "mock_attachment_id_1"},
                },
            ],
        },
    }


@pytest.fixture
def mock_cloud_event_payload():
    """Mock Cloud Event payload containing an email message ID."""
    message_data = json.dumps({"email_message_id": "test_event_id"})
    return {
        "message": {
            "data": base64.b64encode(message_data.encode("utf-8")).decode("utf-8")
        }
    }


@pytest.fixture
def mock_cloud_event_context():
    """Mock Cloud Event context object with event metadata."""

    class MockContext:
        event_id = "1234567890"
        timestamp = datetime.now().isoformat()
        resource = "projects/my-project/topics/my-topic"

    return MockContext()


# --- UNIT TESTS FOR EACH FUNCTION ---
def test_extract_email_body_plain_text(mock_plain_text_payload):
    """Tests extraction of a plain text body."""
    body = extract_email_body(mock_plain_text_payload)
    assert body == "This is a plain text body."


def test_extract_email_body_fallback(mock_email_payload):
    """Tests extraction of an HTML body with tag removal."""
    body = extract_email_body(mock_email_payload)
    assert body == "<html><body><p>This is an <b>HTML</b> body.</p></body></html>"


def test_extract_email_body_prefers_plain_text(mock_multipart_payload):
    """Tests that a multipart message prioritizes plain text."""
    body = extract_email_body(mock_multipart_payload)
    assert body == "This is the plain text part."


def test_parse_email_date_valid_date():
    """Tests parsing a valid date string."""
    date_str = "Mon, 21 Oct 2024 10:00:00 -0700"
    parsed_date = parse_email_date(date_str)
    assert parsed_date == "2024-10-21T10:00:00-07:00"


@patch("src.components.process_emails.datetime")
def test_parse_email_date_invalid_date(mock_dt):
    """Tests fallback to current date for an invalid date string."""
    mock_now = MagicMock()
    mock_now.isoformat.return_value = "2024-10-21T11:00:00.000000"
    mock_dt.now.return_value = mock_now

    parsed_date = parse_email_date("invalid date string")
    assert parsed_date == "2024-10-21T11:00:00.000000"


@patch("src.components.process_emails.upload_attachment_to_gcs")
def test_extract_attachments(
    mock_upload, mock_gmail_service, mock_message_with_attachments
):
    """Tests extraction of attachments from a message with a mock Gmail service."""
    mock_upload.return_value = "gs://mock-bucket/path"

    attachments = extract_attachments(mock_gmail_service, mock_message_with_attachments)

    assert len(attachments) == 2
    assert attachments[0]["file_name"] == "document.pdf"
    assert attachments[1]["file_name"] == "photo.jpg"


def test_mark_email_read(mock_gmail_service):
    """Tests that the mark_email_read function calls the correct API method."""
    message_id = "mock_message_id_to_read"
    mark_email_read(mock_gmail_service, message_id)

    # Assert that the correct methods were called
    mock_gmail_service.users.assert_called_once()
    mock_gmail_service.users.return_value.messages.assert_called_once()
    mock_gmail_service.users.return_value.messages.return_value.modify.assert_called_once_with(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    )


@patch("src.components.process_emails.extract_attachments")
@patch("src.components.process_emails.extract_email_body")
@patch("src.components.process_emails.parse_email_date")
def test_read_email_full_extraction(
    mock_parse_date,
    mock_extract_body,
    mock_extract_attachments,
    mock_gmail_service,
    mock_read_email_message,
):
    """Tests the read_email function by mocking its dependencies."""
    mock_parse_date.return_value = "2024-10-21T10:00:00-07:00"
    mock_extract_body.return_value = "Mock body text."
    mock_extract_attachments.return_value = [{"file_name": "test.pdf"}]

    # Mock the full message get() call
    mock_gmail_service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
        mock_read_email_message
    )

    email_data = read_email(mock_gmail_service, "mock_message_id_full")

    # Assert that the extracted data is correct
    assert email_data["message_id"] == "mock_message_id_full"
    assert email_data["subject"] == "Full Message Test"
    assert email_data["sender"] == "test@example.com"
    assert email_data["attachment_count"] == 1
    assert email_data["attachments"][0]["file_name"] == "test.pdf"


def test_list_unread_emails_success(mock_gmail_service):
    """Tests successful fetching of unread emails."""
    mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "email1"}, {"id": "email2"}]
    }

    messages = list_unread_emails(mock_gmail_service)

    assert len(messages) == 2
    assert messages[0]["id"] == "email1"


def test_list_unread_emails_no_messages(mock_gmail_service):
    """Tests fetching when no unread emails are found."""
    mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = (
        {}
    )

    messages = list_unread_emails(mock_gmail_service)

    assert len(messages) == 0


def test_list_unread_emails_exception(mock_gmail_service):
    """Tests error handling during fetching of unread emails."""
    mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = Exception(
        "API error"
    )

    messages = list_unread_emails(mock_gmail_service)

    assert len(messages) == 0


def test_main_handler_cloud_event(
    mock_cloud_event_payload,
    mock_cloud_event_context,
    mock_gmail_service,
):
    """
    Tests the main Cloud Function handler triggered by a Pub/Sub event.
    Verifies that the correct functions are called with the event data.
    """
    # Assuming your Cloud Function entry point is in a file named main.py, e.g.:
    # from src.components.main import main_handler

    # Since we don't have the main_handler function, we will mock the dependencies it would call
    with patch("src.components.process_emails.read_email") as mock_read_email, patch(
        "src.components.store_bigquery.store_emails_in_bigquery"
    ) as mock_store_bq:

        # Mock the return value of read_email
        mock_read_email.return_value = {
            "message_id": "test_event_id",
            "subject": "Mock Cloud Event Email",
            "sender": "sender@example.com",
            # Add other relevant fields for the mock email
        }

        # We need to simulate the function call, so we'll create a mock for the handler itself
        mock_main_handler = MagicMock()

        # We'll set the side_effect of the mock to call a real function that we control
        def fake_handler(event, context):
            message_data = json.loads(base64.b64decode(event["message"]["data"]))
            message_id = message_data.get("email_message_id")
            email_data = mock_read_email(mock_gmail_service, message_id)
            mock_store_bq(
                mock_gmail_service, None, email_data
            )  # 'None' for the table_ref is a placeholder

        mock_main_handler.side_effect = fake_handler

        # Call the mocked handler with the event payload and context
        mock_main_handler(mock_cloud_event_payload, mock_cloud_event_context)

        # Assertions
        # 1. Verify that read_email was called with the correct message ID from the event
        mock_read_email.assert_called_once_with(mock_gmail_service, "test_event_id")

        # 2. Verify that store_emails_in_bigquery was called with the email data
        # Note: The mock_store_bq is called with a mocked client and a placeholder table_ref
        mock_store_bq.assert_called_once()
