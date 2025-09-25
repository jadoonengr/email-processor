import logging
from google.cloud import secretmanager


# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


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
