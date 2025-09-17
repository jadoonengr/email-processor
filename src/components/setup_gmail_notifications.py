import logging
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Steps in bash to enable Gmail API and create Pub/Sub topic:
"""
# Enable both APIs in your Google Cloud project
gcloud services enable gmail.googleapis.com
gcloud services enable pubsub.googleapis.com
# Create the topic
gcloud pubsub topics create email-notifier

# Create a subscription to consume messages
gcloud pubsub subscriptions create email-notifier-sub --topic=email-notifier

gcloud pubsub topics add-iam-policy-binding email-notifier \
    --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
    --role=roles/pubsub.publisher
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_gmail_push_notifications(
    service,
    user_id="me",
):
    """Set up Gmail push notifications to Pub/Sub topic"""
    # Configure the push notification request
    request_body = {
        "labelIds": ["INBOX"],  # Monitor specific labels
        "topicName": "projects/alpine-comfort-470817-s8/topics/email-notifier",
    }

    # Start watching for changes
    result = service.users().watch(userId=user_id, body=request_body).execute()

    logger.info(
        f"Push notification setup successful. History ID: {result['historyId']}"
    )
    return result


def stop_gmail_push_notifications(service, user_id="me"):
    """Stop Gmail push notifications"""

    # service = build("gmail", "v1", credentials=credentials)

    service.users().stop(userId=user_id).execute()
    logger.info("Push notifications stopped")
