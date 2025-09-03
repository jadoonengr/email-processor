import os
import json
import base64
import re
from datetime import datetime
from googleapiclient.discovery import build
from typing import Dict, Any, List

from src.components.store_gcs import upload_attachment_to_gcs


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
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        return datetime.utcnow().isoformat()


def download_and_upload_attachment(
    gmail_service,
    storage_client,
    bucket,
    message_id: str,
    attachment_id: str,
    filename: str,
    mime_type: str,
) -> Dict[str, Any]:
    """Download attachment from Gmail and upload to GCS."""
    try:
        # Get attachment from Gmail
        attachment = (
            gmail_service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

        file_data = base64.urlsafe_b64decode(attachment["data"])

        # Upload to GCS
        gcs_url = upload_attachment_to_gcs(
            storage_client, bucket, file_data, filename, message_id
        )

        return {
            "filename": filename,
            "mime_type": mime_type,
            "size": len(file_data),
            "gcs_url": gcs_url,
            "uploaded_successfully": gcs_url is not None,
            "attachment_id": attachment_id,
        }

    except Exception as e:
        print(f"  ✗ Error processing {filename}: {e}")
        return {
            "filename": filename,
            "mime_type": mime_type,
            "size": 0,
            "gcs_url": None,
            "uploaded_successfully": False,
            "attachment_id": attachment_id,
            "error": str(e),
        }


def extract_attachments(
    gmail_service, storage_client, bucket, message: Dict, message_id: str
) -> List[Dict[str, Any]]:
    """Extract all attachments from email and upload to GCS."""
    attachments = []

    def process_parts(parts):
        for part in parts:
            if "parts" in part:
                process_parts(part["parts"])
            elif part.get("filename") and part.get("body", {}).get("attachmentId"):
                attachment_info = download_and_upload_attachment(
                    gmail_service,
                    storage_client,
                    bucket,
                    message_id,
                    part["body"]["attachmentId"],
                    part["filename"],
                    part.get("mimeType", "application/octet-stream"),
                )
                attachments.append(attachment_info)

    payload = message.get("payload", {})

    if "parts" in payload:
        process_parts(payload["parts"])
    elif payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        attachment_info = download_and_upload_attachment(
            gmail_service,
            storage_client,
            bucket,
            message_id,
            payload["body"]["attachmentId"],
            payload["filename"],
            payload.get("mimeType", "application/octet-stream"),
        )
        attachments.append(attachment_info)

    return attachments


def parse_email(gmail_service, storage_client, bucket, message: Dict) -> Dict[str, Any]:
    """Parse Gmail message and extract attachments to GCS."""
    headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}

    # Extract attachments
    attachments = extract_attachments(
        gmail_service, storage_client, bucket, message, message["id"]
    )

    # Prepare attachment summary
    attachment_summary = []
    total_attachment_size = 0
    successful_uploads = 0

    for att in attachments:
        attachment_summary.append(
            {
                "filename": att["filename"],
                "mime_type": att["mime_type"],
                "size": att["size"],
                "gcs_url": att["gcs_url"],
                "uploaded_successfully": att["uploaded_successfully"],
            }
        )
        total_attachment_size += att["size"]
        if att["uploaded_successfully"]:
            successful_uploads += 1

    if attachments:
        print(
            f"  📎 {len(attachments)} attachments, {successful_uploads} uploaded successfully"
        )

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
        "attachment_summary": json.dumps(attachment_summary),
        "total_attachment_size": total_attachment_size,
        "successful_uploads": successful_uploads,
        "processed_at": datetime.utcnow().isoformat(),
    }


def get_unread_emails(
    gmail_service, storage_client, bucket, max_results: int = 100
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
        print(f"📧 Found {len(messages)} unread emails")

        email_data = []

        for i, message in enumerate(messages, 1):
            print(f"\n[{i}/{len(messages)}] Processing message {message['id'][:8]}...")

            # Get full message
            msg = (
                gmail_service.users()
                .messages()
                .get(userId="me", id=message["id"], format="full")
                .execute()
            )

            # Parse email and process attachments
            parsed_email = parse_email(gmail_service, storage_client, bucket, msg)
            email_data.append(parsed_email)

        return email_data

    except Exception as error:
        print(f"❌ Error fetching emails: {error}")
        return []
