import pytest
from unittest import mock
import json
from main import process_email

# --- Test Data ---
# A simple mock email without an attachment.
# The content is a base64-encoded string of a simple email.
mock_raw_email_no_attachment_b64 = "RnJvbTogSm9obiBEb2UgfGdkYXRhfGdsYW5kdXB0ZXJAY3dhb20ubmV0PiBXZWJzaXRlOiBzaW1wbGUuY29tDQpUbyA6IENvbnRhY3QgPGV4YW1wbGVAY29udGFjdC5jb20+DQpTdWJqZWN0OiBUZXN0IEVtYWlsIEdJVCBPdXRyZWFjaGVzDQpEYXRlOiBTdW4sIDMxIE9jdCAyMDI1IDIxOjA5OjQ4IC0wNDAwDQoNClRoaXMgaXMgYSB0ZXN0IGJvZHku"

# A mock email with a text attachment.
mock_raw_email_with_attachment_b64 = (
    "RnJvbTogSm9obiBEb2UgPGV4YW1wbGVAc2lnbnVwLmNvbT4NCgpUbyA6IENvbnRhY3QgPGV4YW1wbG"
    "VAY29udGFjdC5jb20+DQpTdWJqZWN0OiBUZXN0IGVtYWlsIHdpdGggYXR0YWNobWVudA0KQ29udGV"
    "udC1UeXBlOiBtdWx0aXBhcnQvbWl4ZWQ7IGJvdW5kYXJ5PSJfMDAxX2VlMzMxMTQ3MTcxZmQ3NDJi"
    "ZWM5YTZiMDZjZWZkNDU5YTRiMDAxYzU2XyINCg0KLS0wMDFfZWUzMzExNDcxNzFmZDc0MmJlYzlhN"
    "mIwNmNlZmQ0NTlhNGIwMDFjNTZfDQpDb250ZW50LVR5cGU6IHRleHQvcGxhaW47IGNoYXJzZXQ9IlV"
    "URi04Ig0KQ29udGVudC1UcmFuc2Zlci1FbmNvZGluZzogcXVvdGVkLXByaW50YWJsZQ0KDQpUaGlz"
    "IGlzIHRoZSBtYWluIGJvZHkgb2YgdGhlIGVtYWlsLg0KDQotLTAwMV9lZTMzMTE0NzE3MWZkNzQyY"
    "mVjOWE2YjA2Y2VmZDQ1OWE0YjAwMWM1Nl8NCkNvbnRlbnQtVHlwZTogdGV4dC9wbGFpbjtgbmFtZT"
    "0iYXR0YWNobWVudC50eHQiDQpDb250ZW50LURpc3Bvc2l0aW9uOiBhdHRhY2htZW50OyBmaWxlbmF"
    "tZT0iYXR0YWNobWVudC50eHQiDQpDb250ZW50LVRyYW5zZmVyLUVuY29kaW5nOiBiYXNlNjQNCg0K"
    "SGVsbG8sIHRoaXMgc2hvdWxkIGJlIHRoZSByYXcgYXR0YWNobWVudCBjb250ZW50Lg0KDQotLTAwM"
    "V9lZTMzMTE0NzE3MWZkNzQyYmVjOWE2YjA2Y2VmZDQ1OWE0YjAwMWM1Nl9f"
)

PROJECT_ID = 'hallowed-glider-460000-q8'
BIGQUERY_DATASET = 'insurance_dataset'
BIGQUERY_TABLE = 'gmail_raw_emails'
GCS_BUCKET_NAME = 'gmail-email-attachments-bucket'


@pytest.fixture
def mock_request():
    """Fixture to create a mock Flask request object."""
    mock_req = mock.Mock()
    mock_req.is_json = True
    return mock_req


@mock.patch("google.cloud.bigquery.Client")
@mock.patch("google.cloud.storage.Client")
@mock.patch("os.environ.get")
def test_process_email_no_attachments_success(mock_env, mock_storage_client, mock_bq_client, mock_request):
    """
    Tests the happy path for an email without any attachments.
    Verifies that the BigQuery client's insert method is called once.
    """
    # Mock environment variables
    mock_env.side_effect = [PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE, GCS_BUCKET_NAME]

    # Set up the mock request object with valid data
    mock_request.get_json.return_value = {'raw_email': mock_raw_email_no_attachment_b64}

    # Call the function under test
    response, status_code = process_email(mock_request)

    # Assertions
    assert status_code == 200
    assert "successfully processed" in response
    
    # Verify that BigQuery insert was called once with the correct data
    mock_bq_client.return_value.insert_rows_json.assert_called_once()
    
    # Verify that GCS upload was NOT called, as there were no attachments
    mock_storage_client.return_value.bucket.assert_not_called()


@mock.patch("google.cloud.bigquery.Client")
@mock.patch("google.cloud.storage.Client")
@mock.patch("os.environ.get")
def test_process_email_with_attachment_success(mock_env, mock_storage_client, mock_bq_client, mock_request):
    """
    Tests the happy path for an email with an attachment.
    Verifies that both BigQuery and GCS methods are called.
    """
    # Mock environment variables
    mock_env.side_effect = ['project-id', 'dataset', 'table', 'bucket']

    # Set up the mock request object with valid data and an attachment
    mock_request.get_json.return_value = {'raw_email': mock_raw_email_with_attachment_b64}

    # Mock the GCS client and its methods
    mock_blob = mock.Mock()
    mock_storage_client.return_value.bucket.return_value.blob.return_value = mock_blob

    # Call the function under test
    response, status_code = process_email(mock_request)

    # Assertions
    assert status_code == 200
    assert "successfully processed" in response
    
    # Verify that GCS upload was called
    mock_storage_client.return_value.bucket.assert_called_once_with('bucket')
    mock_blob.upload_from_string.assert_called_once()

    # Verify that BigQuery insert was called
    mock_bq_client.return_value.insert_rows_json.assert_called_once()
    
    # Verify that the BigQuery row contains attachment info
    call_args = mock_bq_client.return_value.insert_rows_json.call_args[0][1][0]
    attachments_info = json.loads(call_args['attachments_info'])
    assert len(attachments_info) == 1
    assert attachments_info[0]['filename'] == 'attachment.txt'
    assert 'gcs_path' in attachments_info[0]


@mock.patch("main.bigquery_client")
@mock.patch("main.storage_client")
@mock.patch("main.os.environ.get")
def test_process_email_bad_json_request(mock_env, mock_storage_client, mock_bq_client, mock_request):
    """
    Tests handling of a request that is not valid JSON.
    """
    mock_request.is_json = False
    response, status_code = process_email(mock_request)
    assert status_code == 400
    assert "Request body must be a JSON object." in response


@mock.patch("main.bigquery_client")
@mock.patch("main.storage_client")
@mock.patch("main.os.environ.get")
def test_process_email_missing_raw_email(mock_env, mock_storage_client, mock_bq_client, mock_request):
    """
    Tests handling of a request with a missing 'raw_email' key.
    """
    mock_request.get_json.return_value = {'some_other_key': 'value'}
    response, status_code = process_email(mock_request)
    assert status_code == 400
    assert "Missing 'raw_email' in the request body." in response


@mock.patch("main.bigquery_client")
@mock.patch("main.storage_client")
@mock.patch("main.os.environ.get")
def test_process_email_invalid_base64_data(mock_env, mock_storage_client, mock_bq_client, mock_request):
    """
    Tests handling of a request with an invalid base64 string.
    """
    mock_request.get_json.return_value = {'raw_email': 'invalid-base64-string'}
    response, status_code = process_email(mock_request)
    assert status_code == 400
    assert "Bad Request: Invalid base64-encoded string" in response
