import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud import storage

from src.config import config, ENV
from src.components.secret_manager import download_secret, upload_secret


# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


def authenticate_gmail():
    """Authenticate with Gmail API using OAuth2"""
    # Load parameters
    PROJECT_ID = config[ENV]["PROJECT_ID"]
    CREDENTIALS_FILE = config[ENV]["CREDENTIALS_FILE"]
    SECRET_NAME = config[ENV]["SECRET_NAME"]
    GMAIL_SCOPES = [config[ENV]["GMAIL_SCOPES"]]

    current_directory = os.getcwd()
    parent_directory = os.path.dirname(current_directory)
    credentials_file_path = f"{parent_directory}/{CREDENTIALS_FILE}"

    try:
        # Load token data from Secret Manager
        token_data = download_secret(PROJECT_ID, SECRET_NAME)
        if token_data:
            token_value = json.loads(token_data)
            # Create Credentials object from the parsed JSON dictionary
            token_obj = Credentials.from_authorized_user_info(token_value, GMAIL_SCOPES)

            if not token_obj or not token_obj.valid:
                if token_obj and token_obj.expired and token_obj.refresh_token:
                    token_obj.refresh(Request())
                    logger.info("Refreshed existing credentials")

        else:
            # If there are no valid credentials, request authorization
            logger.warning("Unable to load token data from Secret Manager.")

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file_path, GMAIL_SCOPES
            )
            token_obj = flow.run_local_server(port=0)
            logger.info("Successfully created new token from the Gmail credentials!")

        if token_obj:
            # Save refreshed credentials for next run
            upload_secret(PROJECT_ID, SECRET_NAME, token_obj.to_json())

        # Build the Gmail service
        gmail_service = build("gmail", "v1", credentials=token_obj)
        logger.info("Gmail authentication successful!")
        return gmail_service

    except Exception as e:
        logger.error(f"Gmail authentication failed with error: {e}")
        return None


def authenticate_bigquery(project_id):
    """Initialize BigQuery client"""
    try:
        bigquery_client = bigquery.Client(project=project_id)
        logger.info("BigQuery client initialized!")
        return bigquery_client

    except Exception as e:
        logger.error(f"BigQuery authentication failed with error: {e}")
        return None


def authenticate_gcs(project_id):
    """Initialize Google Cloud Storage client"""
    try:
        storage_client = storage.Client()
        logger.info("Google Cloud Storage client initialized!")
        return storage_client

    except Exception as e:
        logger.error(f"Google Cloud Storage authentication failed with error: {e}")
        return None
