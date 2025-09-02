import json
import os
import functions_framework
from datetime import datetime

from src.config import config, ENV
from src.utils.file_utils import decode_base64
from src.components.auth_services import authenticate_gmail, authenticate_bigquery
from src.components.process_emails import get_unread_emails
from src.components.store_bigquery import store_emails_in_bigquery

# --- Configuration ---
# Configuration parameters
PROJECT_ID = config[ENV]['PROJECT_ID']
GCS_BUCKET_NAME = config[ENV]['GCS_BUCKET_NAME']
BIGQUERY_DATASET = config[ENV]['BIGQUERY_DATASET']      
BIGQUERY_TABLE = config[ENV]['BIGQUERY_TABLE']
    


# --- Main Function ---
@functions_framework.cloud_event
def process_email(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message from Gmail.
    This function uses the Gmail API to retrieve and process email data.

    Args:
        cloud_event (functions_framework.cloud_event.CloudEvent): The CloudEvent object.
    """
    try:
        # The Pub/Sub message contains the user and message ID
        raw_email_data_b64 = cloud_event.data["message"]["data"]
        raw_email_data = decode_base64(raw_email_data_b64)
        message = json.loads(raw_email_data)
        user_id = message.get("emailAddress")
        
        # Authenticate services
        gmail_service = authenticate_gmail()
        bigquery_client = authenticate_bigquery(PROJECT_ID)
        
        # Fetch unread emails
        emails = get_unread_emails(gmail_service)

        if emails:
            # Store in BigQuery
            table_ref = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
            store_emails_in_bigquery(bigquery_client, table_ref, emails)
            print(f"Processing complete! Processed {len(emails)} emails.")
        else:
            print("No unread emails found.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
