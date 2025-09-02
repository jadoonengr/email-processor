import os
import json
import base64
import re   
from datetime import datetime
from googleapiclient.discovery import build 
import googleapiclient.errors

def extract_email_body(payload):
    """Extract text content from email payload."""
    body = ""
    
    if 'parts' in payload:
        # Multipart message
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body += base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8')
            elif part['mimeType'] == 'text/html' and not body:
                # Fallback to HTML if no plain text
                if 'data' in part['body']:
                    html_body = base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8')
                    # Basic HTML tag removal
                    body = re.sub('<[^<]+?>', '', html_body)
    else:
        # Single part message
        if payload['mimeType'] == 'text/plain':
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8')
    
    return body.strip()


def parse_email_date(date_str):
    """Parse email date string to ISO format."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except:
        return datetime.utcnow().isoformat()


def parse_email(message):
    """
    Parse Gmail API message into structured data.
    
    Args:
        message: Gmail API message object
        
    Returns:
        Dictionary with parsed email data
    """
    headers = message['payload'].get('headers', [])
    
    # Extract header information
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
    recipient = next((h['value'] for h in headers if h['name'] == 'To'), '')
    date_received = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
    
    # Parse email body
    body_text = extract_email_body(message['payload'])
    
    # Extract additional metadata
    thread_id = message.get('threadId', '')
    label_ids = message.get('labelIds', [])
    
    # Parse date
    parsed_date = parse_email_date(date_received)
    
    return {
        'message_id': message['id'],
        'thread_id': thread_id,
        'subject': subject,
        'sender': sender,
        'recipient': recipient,
        'date_received': date_received,
        'parsed_date': parsed_date,
        'body_text': body_text,
        'label_ids': json.dumps(label_ids),
        'snippet': message.get('snippet', ''),
        'message_size': message.get('sizeEstimate', 0),
        'processed_at': datetime.utcnow().isoformat()
    }


def get_unread_emails(gmail_service, max_results=100):
    """
    Fetch unread emails from Gmail.
    
    Args:
        gmail_service: Authenticated Gmail service object
        max_results: Maximum number of emails to fetch
        
    Returns:
        List of email dictionaries with parsed content
    """
    try:
        # Search for unread emails
        results = gmail_service.users().messages().list(
            userId='me', 
            q='is:unread',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        print(f"Found {len(messages)} unread emails")
        
        email_data = []
        
        for message in messages:
            msg_id = message['id']
            
            # Get full message details
            msg = gmail_service.users().messages().get(
                userId='me', 
                id=msg_id,
                format='full'
            ).execute()
            
            # Parse email data
            parsed_email = parse_email(msg)
            email_data.append(parsed_email)
            
        return email_data
        
    except Exception as error:
        print(f"An error occurred while fetching emails: {error}")
        return []

