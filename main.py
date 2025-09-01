import base64
import json
import os
import email
from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime
import functions_framework

# --- Configuration ---
# Replace these with your actual project, dataset, table, and bucket names.
# You can set these as environment variables in the Cloud Function settings.
PROJECT_ID = os.environ.get('GCP_PROJECT', 'hallowed-glider-460000-q8')
BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', 'insurance_dataset')
BIGQUERY_TABLE = os.environ.get('BIGQUERY_TABLE', 'gmail_raw_emails')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'gmail-email-attachments-bucket')

# Instantiate BigQuery and Cloud Storage clients
bigquery_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

# Define the BigQuery table schema
# Note: You should create this table in BigQuery before deploying the function.
# Schema:
# - raw_email_data: STRING (to store the full email content)
# - attachments_info: STRING (to store a JSON string of attachment metadata)
# - received_timestamp: TIMESTAMP (to record when the email was processed)
TABLE_REF = bigquery_client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)

@functions_framework.http
def process_email(request):
    """
    HTTP Cloud Function that processes an incoming email.

    The request body is expected to be a JSON object with a 'raw_email' key
    containing the raw, base64-encoded email data.

    Args:
        request (flask.Request): The HTTP request object.
                                 The request body should contain a JSON payload
                                 like: {"raw_email": "SGVsbG8gV29ybGQh..."}

    Returns:
        str: A message indicating the success or failure of the operation.
        int: The HTTP status code.
    """
    try:
        # Check if the request body is valid JSON
        if not request.is_json:
            raise ValueError("Request body must be a JSON object.")

        request_json = request.get_json(silent=True)
        raw_email_data_b64 = request_json.get('raw_email')

        if not raw_email_data_b64:
            raise ValueError("Missing 'raw_email' in the request body.")

        # Decode the base64 email data
        raw_email_data = base64.urlsafe_b64decode(raw_email_data_b64).decode('utf-8')

        # Parse the email using Python's built-in email module
        msg = email.message_from_string(raw_email_data)

        attachments_info = []

        # Iterate over the email parts to find attachments
        for part in msg.walk():
            # Check if the part is an attachment
            if part.get_filename():
                filename = part.get_filename()
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)

                if payload:
                    # Upload the attachment to Cloud Storage
                    bucket = storage_client.bucket(GCS_BUCKET_NAME)
                    # Create a unique blob name to avoid overwrites
                    timestamp_str = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                    blob_name = f'attachments/{timestamp_str}_{filename}'
                    blob = bucket.blob(blob_name)
                    blob.upload_from_string(payload, content_type=content_type)
                    print(f"Uploaded attachment '{filename}' to gs://{GCS_BUCKET_NAME}/{blob_name}")

                    # Store attachment metadata
                    attachments_info.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size_bytes": len(payload),
                        "gcs_path": f"gs://{GCS_BUCKET_NAME}/{blob_name}"
                    })

        # Prepare the row for insertion into BigQuery
        row_to_insert = {
            "raw_email_data": raw_email_data,
            "attachments_info": json.dumps(attachments_info),
            "received_timestamp": datetime.now().isoformat()
        }

        # Insert the row into the BigQuery table
        errors = bigquery_client.insert_rows_json(
            TABLE_REF,
            [row_to_insert],
        )

        if errors:
            print(f"BigQuery insertion failed: {errors}")
            return f"Error: BigQuery insertion failed. Details: {errors}", 500
        else:
            print(f"Successfully processed email and inserted into BigQuery.")
            return "Email successfully processed.", 200

    except ValueError as e:
        print(f"Bad Request: {e}")
        return f"Bad Request: {e}", 400
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"An unexpected error occurred: {e}", 500
