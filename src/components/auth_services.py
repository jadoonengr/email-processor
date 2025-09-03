import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud import storage


def authenticate_gmail(CREDENTIALS_FILE_PATH, GMAIL_SCOPES):
    """Authenticate with Gmail API using OAuth2."""
    creds = None
    token_file = "token.json"

    # Load existing credentials
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE_PATH, GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    gmail_service = build("gmail", "v1", credentials=creds)
    print("Gmail authentication successful!")
    return gmail_service


def authenticate_bigquery(project_id):
    """Initialize BigQuery client."""
    bigquery_client = bigquery.Client(project=project_id)
    print("BigQuery client initialized!")
    return bigquery_client


def authenticate_gcs(project_id):
    """Initialize Google Cloud Storage client."""
    storage_client = storage.Client(project=project_id)
    print("Google Cloud Storage client initialized!")
    return storage_client
