import os
import json
import base64
import re
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from googleapiclient.discovery import build
from typing import Dict, Any, List

from src.components.store_gcs import upload_attachment_to_gcs

# Configure logging
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


def extract_email_body(payload):
    """Extract text content from email payload."""
    body = ""

    if "parts" in payload:
        # Multipart message
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part["body"]:
                    body += base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
            elif part["mimeType"] == "text/html" and not body:
                # Fallback to HTML if no plain text
                if "data" in part["body"]:
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                    # Basic HTML tag removal
                    body = re.sub("<[^<]+?>", "", html_body)
    else:
        # Single part message
        if payload["mimeType"] == "text/plain":
            if "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return body.strip()


def parse_email_date(date_str):
    """Parse email date string to ISO format."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        return datetime.now().isoformat()


def extract_attachments(
    gmail_service,
    message: Dict,
) -> List[Dict[str, Any]]:
    """Extract all attachments from email and upload to GCS."""
    message_id = message["id"]
    attachments = []

    def process_parts(parts):
        for part in parts:
            if "parts" in part:
                process_parts(part["parts"])
            elif part.get("filename") and part.get("body", {}).get("attachmentId"):
                # Get attachment from Gmail
                attachment = (
                    gmail_service.users()
                    .messages()
                    .attachments()
                    .get(
                        userId="me",
                        messageId=message_id,
                        id=part["body"]["attachmentId"],
                    )
                    .execute()
                )

                file_data = base64.urlsafe_b64decode(attachment["data"])

                attachment_info = {
                    "file_id": part["body"]["attachmentId"],
                    "file_name": part["filename"],
                    "file_type": part.get("mimeType", "application/octet-stream"),
                    "file_data": file_data,
                }
                attachments.append(attachment_info)

    payload = message.get("payload", {})

    if "parts" in payload:
        process_parts(payload["parts"])
    elif payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        attachment = (
            gmail_service.users()
            .messages()
            .attachments()
            .get(
                userId="me",
                messageId=message_id,
                id=payload["body"]["attachmentId"],
            )
            .execute()
        )

        file_data = base64.urlsafe_b64decode(attachment["data"])

        attachment_info = {
            "file_id": payload["body"]["attachmentId"],
            "file_name": payload["filename"],
            "file_type": payload.get("mimeType", "application/octet-stream"),
            "file_data": file_data,
        }
        attachments.append(attachment_info)

    return attachments


def mark_email_read(gmail_service, message_id):
    # Mark email as read
    gmail_service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    logger.info("✅ Marked as read.")


def read_email(gmail_service, message_id) -> Dict[str, Any]:
    """Extract and return Gmail message with attachments"""
    # Get full message
    message = (
        gmail_service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    # Extract headers
    headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}

    # Extract attachments
    attachments = extract_attachments(gmail_service, message)

    return {
        "message_id": message["id"],
        "thread_id": message.get("threadId", ""),
        "subject": headers.get("Subject", ""),
        "sender": headers.get("From", ""),
        "recipient": headers.get("To", ""),
        "date_received": headers.get("Date", ""),
        "parsed_date": parse_email_date(headers.get("Date", "")),
        "body_text": extract_email_body(message["payload"]),
        "label_ids": json.dumps(message.get("labelIds", [])),
        "snippet": message.get("snippet", ""),
        "message_size": message.get("sizeEstimate", 0),
        "attachment_count": len(attachments),
        "attachments": attachments,
        "processed_at": datetime.now().isoformat(),
    }


def list_unread_emails(
    gmail_service, max_results: int = 100
):  # -> List[Dict[str, Any]]:
    """Fetch unread emails and process attachments."""
    try:
        results = (
            gmail_service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        logger.info(f"📧 Found {len(messages)} unread emails")

        return messages

    except Exception as error:
        logger.error(f"❌ Error fetching emails: {error}")
        return []
