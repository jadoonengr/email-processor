import base64
import os
import logging
from email.utils import parsedate_to_datetime
from datetime import datetime
from google.cloud import secretmanager


# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


def decode_base64(data_b64: str) -> bytes:
    """Decode base64, padding being optional.

    :param data_b64: Base64 data as an ASCII byte string
    :returns: The decoded byte string.
    """

    missing_padding = len(data_b64) % 4
    if missing_padding:
        data_b64 += "=" * (4 - missing_padding)

    # Decode the base64 email data
    raw_data = base64.urlsafe_b64decode(data_b64).decode("utf-8")

    return raw_data


def sanitize_filename(filename):
    """Sanitize filename to be safe for file system."""
    if not filename:
        return "unnamed_attachment"

    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")

    # Limit filename length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[: 200 - len(ext)] + ext

    return filename


def parse_email_date(
    date_str: str,
) -> str:
    """Parse email date string to ISO format."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        return datetime.now().isoformat()


def upload_secret(project_id, secret_name, payload):
    """Upload a new secret version to an existing secret."""
    try:
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret.
        parent = f"projects/{project_id}/secrets/{secret_name}"

        # Convert the string payload to bytes.
        payload_bytes = payload.encode("UTF-8")

        # Add the new secret version.
        response = client.add_secret_version(
            request={"parent": parent, "payload": {"data": payload_bytes}}
        )

        print(f"✅ Added secret version: {response.name}")
        return response

    except Exception as e:
        print(f"❌ Failed to upload secret: {e}")
        return None


def download_secret(project_id, secret_name):
    """Interacts with the Google Secrets Manager and
    downloads the latest version of the given secret."""
    try:
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret version.
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

        # Access the secret version.
        response = client.access_secret_version(request={"name": name})

        # Return the decoded payload.
        payload = response.payload.data.decode("UTF-8")
        logger.info(f"✅ Successfully accessed secret: {secret_name}")
        return payload

    except Exception as e:
        print(f"❌ Failed to download secret: {e}")
        return None
