import pytest
from unittest.mock import MagicMock, patch

# Import the function to be tested.
from src.components.store_gcs import upload_attachment_to_gcs


# --- Fixtures for common setup ---
@pytest.fixture
def mock_storage_client():
    """Fixture to create a mock Google Cloud Storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    # Configure the mock client's methods
    mock_client.get_bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    return mock_client


# --- Test Cases ---
@patch("src.components.store_gcs.datetime.datetime")
def test_upload_attachment_to_gcs_success(mock_dt, mock_storage_client):
    """
    Tests a successful file upload to GCS.
    Verifies that the correct methods are called and a valid URL is returned.
    """
    # Configure the mock datetime object
    mock_dt.now.return_value.strftime.return_value = "2025-09-20"

    # Mock data for the test
    bucket_name = "test-bucket"
    file_name = "test_file.pdf"
    file_data = b"This is test data."
    file_type = "application/pdf"
    message_id = "12345"

    # Call the function under test
    result = upload_attachment_to_gcs(
        mock_storage_client,
        bucket_name,
        file_name,
        file_data,
        file_type,
        message_id,
    )

    # Assertions
    expected_blob_name = f"2025-09-20/{message_id}/{file_name}"
    expected_url = f"gs://{bucket_name}/{expected_blob_name}"

    assert result[1] == expected_url

    # Verify the GCS client methods were called correctly
    mock_storage_client.get_bucket.assert_called_once_with(bucket_name)
    mock_storage_client.get_bucket.return_value.blob.assert_called_once_with(
        expected_blob_name
    )
    mock_storage_client.get_bucket.return_value.blob.return_value.upload_from_string.assert_called_once_with(
        file_data, content_type=file_type
    )


def test_upload_attachment_to_gcs_failure(mock_storage_client):
    """
    Tests the error handling when the GCS upload fails.
    Verifies that the function returns None and logs an error.
    """
    # Mock the client to raise an exception during the upload
    mock_storage_client.get_bucket.side_effect = Exception("Mock GCS error")

    # Mock data for the test
    bucket_name = "test-bucket"
    file_name = "fail_file.txt"
    file_data = b"Some data"
    file_type = "text/plain"
    message_id = "99999"

    # Call the function under test and capture the result
    result = upload_attachment_to_gcs(
        mock_storage_client,
        bucket_name,
        file_name,
        file_data,
        file_type,
        message_id,
    )

    # Assert that the result is None
    assert result[1] is None


@patch(
    "src.components.store_gcs.sanitize_filename",
    return_value="illegal_file 1.jpg",
)
@patch("src.components.store_gcs.datetime.datetime")
def test_upload_attachment_to_gcs_sanitized_filename_with_decorators(
    mock_dt, mock_sanitizer, mock_storage_client
):
    """
    Tests that the filename is sanitized before creating the blob path.
    We mock sanitize_filename to return a specific value.
    """
    # Configure the mock datetime object
    mock_dt.now.return_value.strftime.return_value = "2025-09-21"

    # Mock data for the test
    bucket_name = "test-bucket"
    file_name = "illegal>file 1.jpg"
    file_data = b"data"
    file_type = "image/jpeg"
    message_id = "123456"

    # Call the function under test
    upload_attachment_to_gcs(
        mock_storage_client,
        bucket_name,
        file_name,
        file_data,
        file_type,
        message_id,
    )

    # Assert that the blob was created with the sanitized name
    expected_blob_name = "2025-09-21/123456/illegal_file 1.jpg"
    mock_storage_client.get_bucket.return_value.blob.assert_called_once_with(
        expected_blob_name
    )
