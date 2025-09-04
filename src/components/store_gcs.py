import os
import mimetypes
import base64
from typing import Optional
import datetime

from src.utils.file_utils import sanitize_filename


def get_gcs_attachment_statistics(storage_client, bucket_name):
    """Get statistics about attachments stored in GCS."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix="attachments/"))

        if not blobs:
            return "No attachments found in GCS bucket"

        total_files = len(blobs)
        total_size = sum(blob.size for blob in blobs)

        # Count file types
        file_types = {}
        for blob in blobs:
            filename = blob.name.split("/")[-1]  # Get filename from path
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext:
                file_types[ext] = file_types.get(ext, 0) + 1
            else:
                file_types["no_extension"] = file_types.get("no_extension", 0) + 1

        stats = {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "bucket_name": bucket_name,
        }

        return stats

    except Exception as e:
        return f"Error getting GCS statistics: {e}"


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


def list_recent_attachments(storage_client, bucket_name, limit=10):
    """List recent attachments uploaded to GCS."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix="attachments/", max_results=limit))

        recent_files = []
        for blob in blobs:
            recent_files.append(
                {
                    "name": blob.name,
                    "size_mb": round(blob.size / (1024 * 1024), 3),
                    "created": (
                        blob.time_created.isoformat() if blob.time_created else None
                    ),
                    "content_type": blob.content_type,
                    "public_url": blob.public_url,
                }
            )

        return recent_files

    except Exception as e:
        print(f"Error listing recent attachments: {e}")
        return []


def download_attachment_to_gcs(
    gmail_service, storage_client, bucket, message_id, attachment_id, filename
):
    """
    Download attachment from Gmail and upload directly to GCS.

    Args:
        gmail_service: Authenticated Gmail service
        storage_client: GCS client
        bucket: GCS bucket object
        message_id: Gmail message ID
        attachment_id: Gmail attachment ID
        filename: Original filename

    Returns:
        Dictionary with attachment info including GCS URL
    """
    try:
        # Get attachment data from Gmail
        attachment = (
            gmail_service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

        # Decode attachment data
        file_data = base64.urlsafe_b64decode(attachment["data"])

        # Upload to GCS
        gcs_url = upload_attachment_to_gcs(
            storage_client, bucket, file_data, filename, message_id
        )

        return {
            "filename": filename,
            "size": len(file_data),
            "gcs_url": gcs_url,
            "uploaded_successfully": gcs_url is not None,
        }

    except Exception as e:
        print(f"Error downloading attachment {filename}: {e}")
        return {
            "filename": filename,
            "size": 0,
            "gcs_url": None,
            "uploaded_successfully": False,
            "error": str(e),
        }
