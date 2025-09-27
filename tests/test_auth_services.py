import pytest
import os
import json
from unittest.mock import patch, MagicMock
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud import storage

# Functions to be tested
from src.components.auth_services import (
    authenticate_gmail,
    authenticate_bigquery,
    authenticate_gcs,
)


# Mock configuration and environment variables
@pytest.fixture
def mock_config():
    """Mocks the config dictionary with test values."""
    mock_conf = {
        "DEV": {
            "PROJECT_ID": "mock-project-dev",
            "CREDENTIALS_FILE": "mock_credentials.json",
            "SECRET_NAME": "mock-gmail-token",
            "GMAIL_SCOPES": "https://www.googleapis.com/auth/gmail.readonly",
        },
        "PROD": {
            "PROJECT_ID": "mock-project-prod",
            "CREDENTIALS_FILE": "mock_credentials.json",
            "SECRET_NAME": "mock-gmail-token",
            "GMAIL_SCOPES": "https://www.googleapis.com/auth/gmail.readonly",
        },
    }
    with patch("src.components.auth_services.config", mock_conf), patch(
        "src.components.auth_services.ENV", "DEV"
    ):
        yield


# --- Tests for authenticate_gmail ---


@patch("src.components.auth_services.download_secret")
@patch("src.components.auth_services.upload_secret")
@patch("src.components.auth_services.Credentials")
@patch("src.components.auth_services.build")
@patch("src.components.auth_services.os.path.dirname")
@patch("src.components.auth_services.os.getcwd")
def test_authenticate_gmail_valid_token(
    mock_getcwd,
    mock_dirname,
    mock_build,
    mock_credentials,
    mock_upload_secret,
    mock_download_secret,
    mock_config,
):
    """Tests successful authentication with a valid, non-expired token."""
    mock_getcwd.return_value = "/mock/path"
    mock_dirname.return_value = "/mock"
    mock_download_secret.return_value = '{"token": "valid_token"}'

    mock_token_obj = MagicMock()
    mock_token_obj.valid = True
    mock_credentials.from_authorized_user_info.return_value = mock_token_obj

    mock_gmail_service = MagicMock()
    mock_build.return_value = mock_gmail_service

    service = authenticate_gmail()

    # Assertions
    assert service is mock_gmail_service
    mock_download_secret.assert_called_once_with("mock-project-dev", "mock-gmail-token")
    mock_credentials.from_authorized_user_info.assert_called_once()
    mock_upload_secret.assert_called_once()
    mock_build.assert_called_once_with("gmail", "v1", credentials=mock_token_obj)


@patch("src.components.auth_services.download_secret")
@patch("src.components.auth_services.upload_secret")
@patch("src.components.auth_services.Credentials")
@patch("src.components.auth_services.Request")
def test_authenticate_gmail_expired_token(
    mock_request,
    mock_credentials,
    mock_upload_secret,
    mock_download_secret,
    mock_config,
):
    """Tests successful authentication with an expired but refreshable token."""
    mock_download_secret.return_value = (
        '{"token": "expired_token", "refresh_token": "mock_refresh"}'
    )

    mock_token_obj = MagicMock()
    mock_token_obj.valid = False
    mock_token_obj.expired = True
    mock_token_obj.refresh_token = "mock_refresh"
    mock_credentials.from_authorized_user_info.return_value = mock_token_obj

    with patch("src.components.auth_services.build"):
        authenticate_gmail()

    # Assertions
    mock_token_obj.refresh.assert_called_once()
    mock_upload_secret.assert_called_once()


@patch("src.components.auth_services.download_secret", return_value=None)
@patch("src.components.auth_services.upload_secret")
@patch("src.components.auth_services.Credentials")
@patch("src.components.auth_services.InstalledAppFlow")
def test_authenticate_gmail_no_token(
    mock_flow,
    mock_credentials,
    mock_upload_secret,
    mock_download_secret,
    mock_config,
):
    """Tests new authorization flow when no token is found in Secret Manager."""
    mock_flow_instance = MagicMock()
    mock_flow_instance.run_local_server.return_value = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance

    with patch("src.components.auth_services.build"):
        authenticate_gmail()

    # Assertions
    mock_flow.from_client_secrets_file.assert_called_once()
    mock_flow_instance.run_local_server.assert_called_once()
    mock_credentials.from_authorized_user_info.assert_not_called()
    mock_upload_secret.assert_called_once()


@patch("src.components.auth_services.download_secret", return_value=None)
def test_authenticate_gmail_token_not_found(
    mock_download_secret,
    mock_config,
):
    """Tests handling of missing token data."""
    service = authenticate_gmail()

    assert service is None
    mock_download_secret.assert_called_once()


@patch(
    "src.components.auth_services.download_secret",
    side_effect=Exception("Mock Auth Error"),
)
def test_authenticate_gmail_exception_handling(
    mock_download_secret,
    mock_config,
):
    """Tests exception handling for Gmail authentication."""
    service = authenticate_gmail()

    assert service is None


# --- Tests for authenticate_bigquery ---


@patch("src.components.auth_services.bigquery.Client")
def test_authenticate_bigquery_success(mock_bq_client):
    """Tests successful initialization of BigQuery client."""
    mock_client_instance = MagicMock()
    mock_bq_client.return_value = mock_client_instance

    client = authenticate_bigquery("mock-project-id")

    # Assertions
    assert client is mock_client_instance
    mock_bq_client.assert_called_once_with(project="mock-project-id")


@patch(
    "src.components.auth_services.bigquery.Client", side_effect=Exception("BQ Error")
)
def test_authenticate_bigquery_failure(mock_bq_client):
    """Tests failure during BigQuery client initialization."""
    client = authenticate_bigquery("mock-project-id")

    assert client is None


# --- Tests for authenticate_gcs ---


@patch("src.components.auth_services.storage.Client")
def test_authenticate_gcs_success(mock_gcs_client):
    """Tests successful initialization of Google Cloud Storage client."""
    mock_client_instance = MagicMock()
    mock_gcs_client.return_value = mock_client_instance

    client = authenticate_gcs("mock-project-id")

    # Assertions
    assert client is mock_client_instance
    mock_gcs_client.assert_called_once_with(project="mock-project-id")


@patch(
    "src.components.auth_services.storage.Client", side_effect=Exception("GCS Error")
)
def test_authenticate_gcs_failure(mock_gcs_client):
    """Tests failure during Google Cloud Storage client initialization."""
    client = authenticate_gcs("mock-project-id")

    assert client is None
