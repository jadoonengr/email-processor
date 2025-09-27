import json
import os
import logging
import functions_framework
from datetime import datetime

from src.config import config, ENV
from src.utils.file_utils import decode_base64
from src.components.auth_services import (
    authenticate_gmail,
    authenticate_bigquery,
    authenticate_gcs,
)
from src.components.setup_gmail_notifications import (
    setup_gmail_push_notifications,
    stop_gmail_push_notifications,
)
from src.components.process_emails import (
    list_unread_emails,
    read_email,
    mark_email_read,
)
from src.components.store_gcs import upload_attachment_to_gcs
from src.components.store_bigquery import store_emails_in_bigquery

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# Configuration parameters
PROJECT_ID = config[ENV]["PROJECT_ID"]
GCS_BUCKET_NAME = config[ENV]["GCS_BUCKET_NAME"]
BIGQUERY_DATASET = config[ENV]["BIGQUERY_DATASET"]
BIGQUERY_TABLE = config[ENV]["BIGQUERY_TABLE"]


# --- Main Function ---
@functions_framework.cloud_event
def process_emails(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message from Gmail.
    This function uses the Gmail API to retrieve and process email data.

    Args:
        cloud_event (functions_framework.cloud_event.CloudEvent): The CloudEvent object.
    """
    try:
        # The Pub/Sub message contains the user and message ID
        event_data_b64 = cloud_event.data["message"]["data"]
        event_data = decode_base64(event_data_b64)
        logger.info(event_data)

        logger.info("==============RUNNING CLOUD FUNCTION==============")
        logger.info(
            f"Starting application. Function triggered at {datetime.now().isoformat()}Z"
        )

        # Initialize services
        gmail_service = authenticate_gmail()
        bigquery_client = authenticate_bigquery(PROJECT_ID)
        storage_client = authenticate_gcs(PROJECT_ID)
        if not gmail_service or not bigquery_client or not storage_client:
            logger.warning(
                "One or more services failed to initialize. Exiting function."
            )
            return
        else:
            logger.info("All services initialized successfully.")

        # Setup Gmail push notifications (if needed)
        setup_gmail_push_notifications(gmail_service)
        # stop_gmail_push_notifications(gmail_service, user_id="me")

        # Fetch unread emails list
        emails = list_unread_emails(
            gmail_service,
            max_results=100,
        )

        if not emails:
            logger.info(" 📭 No unread emails found.")

        else:
            logger.info(f"Found {len(emails)} unread messages.")

            for i, email in enumerate(emails, 1):
                logger.info(
                    f"\n[{i}/{len(emails)}] Processing message {email['id'][:8]}..."
                )

                # Read and process each email
                extracted_email = read_email(gmail_service, email["id"])

                # Store attachments to GCS
                attachments = extracted_email.get("attachments", [])

                for attachment in attachments:
                    file_name = attachment["file_name"]
                    file_data = attachment["file_data"]
                    file_type = attachment["file_type"]

                    if not file_data:
                        logger.warning(f" ⚠ No data for attachment: {file_name}")
                    else:
                        gcs_upload_status, gcs_url = upload_attachment_to_gcs(
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
                        if gcs_upload_status and gcs_url:
                            attachment["gcs_url"] = gcs_url
                            logger.info(f" 📎 Attachment uploaded to GCS: {gcs_url}")
                        else:
                            logger.warning(
                                f"  ⚠ Failed to upload attachment: {file_name}"
                            )

                # Store email to BigQuery
                table_ref = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
                bq_upload_status = store_emails_in_bigquery(
                    bigquery_client, table_ref, extracted_email
                )

                # Mark email as read
                if (attachments == [] and bq_upload_status) or (
                    attachments != [] and gcs_upload_status and bq_upload_status
                ):
                    mark_email_read(gmail_service, email["id"])
                    logger.info(f"\n ✅ Processing completed successfully!")
                else:
                    logger.warning(f"\n ⚠ Processing completed with errors!")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
