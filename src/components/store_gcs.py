import os
import mimetypes
import base64
from typing import Optional
import datetime

from src.utils.file_utils import sanitize_filename


def upload_attachment_to_gcs(
    storage_client,
    bucket_name,
    file_name: str,
    file_data: bytes,
    file_type: str,
    message_id: str,
) -> Optional[str]:
    """Upload attachment to GCS and return public URL."""
    try:
        # Create file name with date
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_filename = sanitize_filename(file_name)
        blob_name = f"{curr_date}/{message_id}/{safe_filename}"

        # Get bucket and create blob
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Upload file
        blob.upload_from_string(
            file_data,
            content_type=file_type,  # Must match actual content
        )

        qualified_blob_name = f"gs://{bucket_name}/{blob_name}"
        return qualified_blob_name

    except Exception as e:
        print(f"  ✗ Upload failed for {file_name}: {e}")
        return None
