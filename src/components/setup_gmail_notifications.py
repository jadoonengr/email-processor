import logging
import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from src.config import config, ENV

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
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# Configuration parameters
PROJECT_ID = config[ENV]["PROJECT_ID"]
PUBSUB_TOPIC = config[ENV]["PUBSUB_TOPIC"]


def setup_gmail_push_notifications(gmail_service):
    """Set up Gmail push notifications to Pub/Sub"""
    try:
        # Format the topic name properly
        full_topic_name = f"projects/{PROJECT_ID}/topics/{PUBSUB_TOPIC}"

        request_body = {
            "topicName": full_topic_name,
            "labelIds": ["INBOX"],  # Monitor INBOX only
            "labelFilterAction": "include",
        }

        # Set up the watch
        result = gmail_service.users().watch(userId="me", body=request_body).execute()

        logger.info("✅ Gmail push notifications set up successfully!")
        logger.info(f"History ID: {result['historyId']}")
        logger.info(f"Expiration: {result['expiration']} (timestamp in milliseconds)")

        # Convert expiration to readable date
        expiration_date = datetime.datetime.fromtimestamp(
            int(result["expiration"]) / 1000
        )
        logger.info(f"Expires on: {expiration_date}")
        logger.info("⚠️ Remember to renew before this date!")

        return result
    except Exception as e:
        logger.error(f"Error setting up push notifications: {e}")
        return None


def stop_gmail_push_notifications(gmail_service, user_id="me"):
    """Stop Gmail push notifications"""

    # gmail_service = build("gmail", "v1", credentials=credentials)

    gmail_service.users().stop(userId=user_id).execute()
    logger.info("Push notifications stopped")
