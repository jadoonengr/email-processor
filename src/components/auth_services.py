import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud import storage

from src.config import config, ENV


# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


def authenticate_gmail():
    """Authenticate with Gmail API using OAuth2."""
    # Load parameters
    CREDENTIALS_FILE = config[ENV]["CREDENTIALS_FILE"]
    GMAIL_SCOPES = [config[ENV]["GMAIL_SCOPES"]]

    current_directory = os.getcwd()
    parent_directory = os.path.dirname(current_directory)
    credentials_file_path = f"{parent_directory}/{CREDENTIALS_FILE}"

    try:
        creds = None
        token_file = "token.json"

        # Load existing credentials
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Refreshed existing credentials")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file_path, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Successfully authorized new credentials")

            # Save credentials for next run
            with open(token_file, "w") as token:
                token.write(creds.to_json())
                logger.info("Credentials saved to token.json")

        gmail_service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail authentication successful!")
        return gmail_service

    except Exception as e:
        logger.error(f"Gmail authentication failed with error: {e}")
        return None


def authenticate_bigquery(project_id):
    """Initialize BigQuery client."""
    try:
        bigquery_client = bigquery.Client(project=project_id)
        logger.info("BigQuery client initialized!")
        return bigquery_client

    except Exception as e:
        logger.error(f"BigQuery authentication failed with error: {e}")
        return None


def authenticate_gcs(project_id):
    """Initialize Google Cloud Storage client."""
    try:
        storage_client = storage.Client(project=project_id)
        logger.info("Google Cloud Storage client initialized!")
        return storage_client

    except Exception as e:
        logger.error(f"Google Cloud Storage authentication failed with error: {e}")
        return None
