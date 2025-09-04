import json
import os
import functions_framework
from datetime import datetime

from src.config import config, ENV
from src.utils.file_utils import decode_base64
from src.components.auth_services import (
    authenticate_gmail,
    authenticate_bigquery,
    authenticate_gcs,
)
from src.components.process_emails import list_unread_emails, read_email
from src.components.store_gcs import upload_attachment_to_gcs
from src.components.store_bigquery import store_emails_in_bigquery

# --- Configuration ---
# Configuration parameters
PROJECT_ID = config[ENV]["PROJECT_ID"]
GCS_BUCKET_NAME = config[ENV]["GCS_BUCKET_NAME"]
BIGQUERY_DATASET = config[ENV]["BIGQUERY_DATASET"]
BIGQUERY_TABLE = config[ENV]["BIGQUERY_TABLE"]
CREDENTIALS_FILE_PATH = config[ENV]["CREDENTIALS_FILE_PATH"]
GMAIL_SCOPES = [config[ENV]["GMAIL_SCOPES"]]


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

        # Initialize services
        gmail_service = authenticate_gmail(CREDENTIALS_FILE_PATH, GMAIL_SCOPES)
        bigquery_client = authenticate_bigquery(PROJECT_ID)
        storage_client = authenticate_gcs(PROJECT_ID)

        # Fetch unread emails list
        emails = list_unread_emails(
            gmail_service,
            max_results=100,
        )

        if emails:
            for i, email in enumerate(emails, 1):
                print(f"\n[{i}/{len(emails)}] Processing message {email['id'][:8]}...")

                # Read and process each email
                extracted_email = read_email(gmail_service, email)

                # Store attachments to GCS
                attachments = extracted_email.get("attachments", [])

                for attachment in attachments:
                    file_name = attachment["file_name"]
                    file_data = attachment["file_data"]
                    file_type = attachment["file_type"]

                    if file_data:
                        gcs_url = upload_attachment_to_gcs(
                            storage_client,
                            GCS_BUCKET_NAME,
                            file_name,
                            file_data,
                            file_type,
                            email["id"],
                        )

                        # Remove file data to save space
                        attachment.pop("file_data", None)

                        # Add GCS URL to attachment info
                        if gcs_url:
                            attachment["gcs_url"] = gcs_url
                            print(f"  📎 Attachment uploaded to GCS: {gcs_url}")
                        else:
                            print(f"  ⚠ Failed to upload attachment: {file_name}")
                    else:
                        print(f"  ⚠ No data for attachment: {file_name}")

                # Store email to BigQuery
                table_ref = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
                store_emails_in_bigquery(bigquery_client, table_ref, extracted_email)
                print(f"Processing complete!")
        else:
            print("No unread emails found.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # # Setup infrastructure
    # bucket = setup_gcs_bucket(storage_client)
    # create_bigquery_table(bigquery_client)

    # # Process emails
    # emails = get_unread_emails(gmail_service, storage_client, bucket, max_results)

    # if emails:
    #     # Store in BigQuery
    #     store_emails_in_bigquery(bigquery_client, emails)

    #     # Show statistics
    #     print("\n" + "="*60)
    #     print("📊 PROCESSING SUMMARY")
    #     print("="*60)

    #     gcs_stats = get_gcs_statistics(storage_client)
    #     if 'error' not in gcs_stats:
    #         print(f"GCS Bucket ({GCS_BUCKET_NAME}):")
    #         print(f"  • Total files: {gcs_stats['total_files']}")
    #         print(f"  • Total size: {gcs_stats['total_size_mb']} MB")
    #         print(f"  • File types: {gcs_stats['file_types']}")

    #     # Show recent emails with attachments
    #     query_recent_emails_with_attachments(bigquery_client, limit=3)

    #     print(f"\n✅ Processing completed successfully!")

    # else:
    #     print("📭 No unread emails found.")
