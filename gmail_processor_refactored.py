"""
Gmail to BigQuery Email Processor with GCS Attachment Storage

This module processes unread Gmail emails, extracts attachments to Google Cloud Storage,
and stores email metadata in BigQuery for analysis.
"""

import os
import base64
import json
import re
import mimetypes
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud import storage
from email.utils import parsedate_to_datetime


@dataclass
class Config:
    """Configuration settings for the email processor."""
    credentials_file: str = 'credentials.json'
    token_file: str = 'token.json'
    bigquery_project_id: str = 'your-project-id'
    dataset_id: str = 'email_data'
    table_id: str = 'gmail_emails'
    gcs_bucket_name: str = 'your-email-attachments-bucket'
    scopes: List[str] = None
    max_filename_length: int = 200
    max_body_length: int = 1000000
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']


@dataclass
class AttachmentInfo:
    """Information about an email attachment."""
    filename: str
    mime_type: str
    size: int
    gcs_url: Optional[str] = None
    uploaded_successfully: bool = False
    attachment_id: str = ""
    error: Optional[str] = None


@dataclass
class EmailData:
    """Structured email data for BigQuery storage."""
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date_received: str
    parsed_date: str
    body_text: str
    label_ids: str
    snippet: str
    message_size: int
    attachments: List[AttachmentInfo]
    processed_at: str
    
    @property
    def attachment_count(self) -> int:
        return len(self.attachments)
    
    @property
    def successful_uploads(self) -> int:
        return sum(1 for att in self.attachments if att.uploaded_successfully)
    
    @property
    def total_attachment_size(self) -> int:
        return sum(att.size for att in self.attachments)
    
    @property
    def attachment_summary(self) -> str:
        return json.dumps([
            {
                'filename': att.filename,
                'mime_type': att.mime_type,
                'size': att.size,
                'gcs_url': att.gcs_url,
                'uploaded_successfully': att.uploaded_successfully
            }
            for att in self.attachments
        ])


class AuthenticationManager:
    """Handles authentication for Google services."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def authenticate_gmail(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = self._load_existing_credentials()
        
        if not self._credentials_valid(creds):
            creds = self._refresh_or_create_credentials(creds)
            self._save_credentials(creds)
        
        gmail_service = build('gmail', 'v1', credentials=creds)
        print("✓ Gmail authentication successful")
        return gmail_service
    
    def _load_existing_credentials(self) -> Optional[Credentials]:
        """Load existing credentials from token file."""
        if os.path.exists(self.config.token_file):
            return Credentials.from_authorized_user_file(
                self.config.token_file, self.config.scopes
            )
        return None
    
    def _credentials_valid(self, creds: Optional[Credentials]) -> bool:
        """Check if credentials are valid."""
        return creds and creds.valid
    
    def _refresh_or_create_credentials(self, creds: Optional[Credentials]) -> Credentials:
        """Refresh existing credentials or create new ones."""
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
        
        flow = InstalledAppFlow.from_client_secrets_file(
            self.config.credentials_file, self.config.scopes
        )
        return flow.run_local_server(port=0)
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        with open(self.config.token_file, 'w') as token:
            token.write(creds.to_json())
    
    def authenticate_bigquery(self):
        """Initialize BigQuery client."""
        client = bigquery.Client(project=self.config.bigquery_project_id)
        print("✓ BigQuery client initialized")
        return client
    
    def authenticate_gcs(self):
        """Initialize Google Cloud Storage client."""
        client = storage.Client(project=self.config.bigquery_project_id)
        print("✓ Google Cloud Storage client initialized")
        return client


class FileUtils:
    """Utility functions for file operations."""
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 200) -> str:
        """Sanitize filename for file system safety."""
        if not filename:
            return "unnamed_attachment"
        
        # Remove unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Limit filename length
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def parse_email_date(date_str: str) -> str:
        """Parse email date string to ISO format."""
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except Exception:
            return datetime.utcnow().isoformat()


class GCSManager:
    """Manages Google Cloud Storage operations for attachments."""
    
    def __init__(self, storage_client, config: Config):
        self.storage_client = storage_client
        self.config = config
        self.bucket = self._setup_bucket()
    
    def _setup_bucket(self) -> storage.Bucket:
        """Create or get GCS bucket for attachments."""
        try:
            bucket = self.storage_client.bucket(self.config.gcs_bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(self.config.gcs_bucket_name)
                print(f"✓ Created GCS bucket: {self.config.gcs_bucket_name}")
            else:
                print(f"✓ Using existing GCS bucket: {self.config.gcs_bucket_name}")
            return bucket
        except Exception as e:
            print(f"⚠ Warning: {e}")
            return self.storage_client.bucket(self.config.gcs_bucket_name)
    
    def upload_attachment(self, file_data: bytes, filename: str, message_id: str) -> Optional[str]:
        """Upload attachment to GCS and return public URL."""
        try:
            safe_filename = FileUtils.sanitize_filename(filename, self.config.max_filename_length)
            blob_name = f"attachments/{message_id}/{safe_filename}"
            
            blob = self.bucket.blob(blob_name)
            
            # Set content type
            content_type, _ = mimetypes.guess_type(filename)
            if content_type:
                blob.content_type = content_type
            
            # Upload file
            blob.upload_from_string(file_data)
            blob.make_public()
            
            print(f"  ✓ Uploaded: {filename} -> {blob_name}")
            return blob.public_url
            
        except Exception as e:
            print(f"  ✗ Upload failed for {filename}: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get GCS bucket statistics."""
        try:
            blobs = list(self.bucket.list_blobs(prefix='attachments/'))
            
            if not blobs:
                return {'total_files': 0, 'total_size_mb': 0, 'file_types': {}}
            
            total_size = sum(blob.size for blob in blobs)
            file_types = {}
            
            for blob in blobs:
                filename = blob.name.split('/')[-1]
                _, ext = os.path.splitext(filename)
                ext = ext.lower() or 'no_extension'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_files': len(blobs),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types
            }
            
        except Exception as e:
            print(f"⚠ Error getting GCS stats: {e}")
            return {'error': str(e)}


class EmailParser:
    """Handles parsing of Gmail messages."""
    
    def __init__(self, gmail_service, gcs_manager: GCSManager, config: Config):
        self.gmail_service = gmail_service
        self.gcs_manager = gcs_manager
        self.config = config
    
    def parse_email(self, message: Dict) -> EmailData:
        """Parse Gmail message and extract all relevant data."""
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        
        return EmailData(
            message_id=message['id'],
            thread_id=message.get('threadId', ''),
            subject=headers.get('Subject', ''),
            sender=headers.get('From', ''),
            recipient=headers.get('To', ''),
            date_received=headers.get('Date', ''),
            parsed_date=FileUtils.parse_email_date(headers.get('Date', '')),
            body_text=self._extract_email_body(message['payload']),
            label_ids=json.dumps(message.get('labelIds', [])),
            snippet=message.get('snippet', ''),
            message_size=message.get('sizeEstimate', 0),
            attachments=self._extract_attachments(message, message['id']),
            processed_at=datetime.utcnow().isoformat()
        )
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract text content from email payload, excluding attachments."""
        body = ""
        
        def process_parts_for_body(parts):
            nonlocal body
            for part in parts:
                if 'parts' in part:
                    process_parts_for_body(part['parts'])
                elif self._is_text_part(part):
                    decoded_text = self._decode_part_data(part)
                    if decoded_text:
                        if part['mimeType'] == 'text/plain':
                            body += decoded_text
                        elif part['mimeType'] == 'text/html' and not body:
                            body = self._strip_html_tags(decoded_text)
        
        if 'parts' in payload:
            process_parts_for_body(payload['parts'])
        elif self._is_text_part(payload):
            decoded_text = self._decode_part_data(payload)
            if decoded_text:
                body = decoded_text
        
        return body.strip()
    
    def _is_text_part(self, part: Dict) -> bool:
        """Check if a part contains text content (not attachment)."""
        return (part.get('mimeType') in ['text/plain', 'text/html'] and
                not part.get('filename') and
                'data' in part.get('body', {}))
    
    def _decode_part_data(self, part: Dict) -> Optional[str]:
        """Decode base64 data from email part."""
        try:
            decoded = base64.urlsafe_b64decode(part['body']['data'])
            return decoded.decode('utf-8', errors='ignore')
        except Exception:
            return None
    
    def _strip_html_tags(self, html_text: str) -> str:
        """Remove HTML tags from text."""
        return re.sub('<[^<]+?>', '', html_text)
    
    def _extract_attachments(self, message: Dict, message_id: str) -> List[AttachmentInfo]:
        """Extract all attachments from email and upload to GCS."""
        attachments = []
        
        def process_parts(parts):
            for part in parts:
                if 'parts' in part:
                    process_parts(part['parts'])
                elif self._is_attachment_part(part):
                    attachment_info = self._process_attachment(
                        message_id, part['body']['attachmentId'],
                        part['filename'], part.get('mimeType', 'application/octet-stream')
                    )
                    attachments.append(attachment_info)
        
        payload = message.get('payload', {})
        
        if 'parts' in payload:
            process_parts(payload['parts'])
        elif self._is_attachment_part(payload):
            attachment_info = self._process_attachment(
                message_id, payload['body']['attachmentId'],
                payload['filename'], payload.get('mimeType', 'application/octet-stream')
            )
            attachments.append(attachment_info)
        
        if attachments:
            successful = sum(1 for att in attachments if att.uploaded_successfully)
            print(f"  📎 {len(attachments)} attachments, {successful} uploaded successfully")
        
        return attachments
    
    def _is_attachment_part(self, part: Dict) -> bool:
        """Check if a part is an attachment."""
        return (part.get('filename') and 
                part.get('body', {}).get('attachmentId'))
    
    def _process_attachment(self, message_id: str, attachment_id: str, 
                          filename: str, mime_type: str) -> AttachmentInfo:
        """Download attachment from Gmail and upload to GCS."""
        try:
            # Get attachment from Gmail
            attachment = self.gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            # Upload to GCS
            gcs_url = self.gcs_manager.upload_attachment(file_data, filename, message_id)
            
            return AttachmentInfo(
                filename=filename,
                mime_type=mime_type,
                size=len(file_data),
                gcs_url=gcs_url,
                uploaded_successfully=gcs_url is not None,
                attachment_id=attachment_id
            )
            
        except Exception as e:
            print(f"  ✗ Error processing {filename}: {e}")
            return AttachmentInfo(
                filename=filename,
                mime_type=mime_type,
                size=0,
                gcs_url=None,
                uploaded_successfully=False,
                attachment_id=attachment_id,
                error=str(e)
            )


class BigQueryManager:
    """Manages BigQuery operations for email storage."""
    
    def __init__(self, bigquery_client, config: Config):
        self.bigquery_client = bigquery_client
        self.config = config
        self.table_ref = self.bigquery_client.dataset(config.dataset_id).table(config.table_id)
    
    def create_table(self):
        """Create BigQuery table with proper schema."""
        schema = [
            bigquery.SchemaField("message_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("thread_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("subject", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("sender", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("recipient", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("date_received", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("parsed_date", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("body_text", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("label_ids", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("snippet", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("message_size", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("attachment_count", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("attachment_summary", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("total_attachment_size", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("successful_uploads", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("processed_at", "TIMESTAMP", mode="NULLABLE"),
        ]
        
        table = bigquery.Table(self.table_ref, schema=schema)
        
        try:
            self.bigquery_client.create_table(table)
            print(f"✓ Created BigQuery table: {self.config.dataset_id}.{self.config.table_id}")
        except Exception as e:
            if "Already Exists" in str(e):
                print(f"✓ BigQuery table exists: {self.config.dataset_id}.{self.config.table_id}")
            else:
                raise e
    
    def store_emails(self, emails: List[EmailData]):
        """Store email data in BigQuery."""
        if not emails:
            print("⚠ No emails to store")
            return
        
        rows_to_insert = [self._email_to_bigquery_row(email) for email in emails]
        
        errors = self.bigquery_client.insert_rows_json(self.table_ref, rows_to_insert)
        
        if errors:
            print(f"❌ BigQuery insertion errors: {errors}")
        else:
            total_attachments = sum(email.attachment_count for email in emails)
            total_successful = sum(email.successful_uploads for email in emails)
            
            print(f"✓ Stored {len(emails)} emails in BigQuery")
            if total_attachments > 0:
                print(f"  📎 {total_successful}/{total_attachments} attachments uploaded successfully")
    
    def _email_to_bigquery_row(self, email: EmailData) -> Dict[str, Any]:
        """Convert EmailData to BigQuery row format."""
        return {
            'message_id': email.message_id,
            'thread_id': email.thread_id,
            'subject': email.subject,
            'sender': email.sender,
            'recipient': email.recipient,
            'date_received': email.date_received,
            'parsed_date': email.parsed_date,
            'body_text': email.body_text[:self.config.max_body_length] if email.body_text else None,
            'label_ids': email.label_ids,
            'snippet': email.snippet,
            'message_size': email.message_size,
            'attachment_count': email.attachment_count,
            'attachment_summary': email.attachment_summary,
            'total_attachment_size': email.total_attachment_size,
            'successful_uploads': email.successful_uploads,
            'processed_at': email.processed_at
        }
    
    def query_recent_emails_with_attachments(self, limit: int = 5):
        """Query recent emails with attachments."""
        query = f"""
        SELECT 
            message_id,
            subject,
            sender,
            attachment_count,
            successful_uploads,
            attachment_summary,
            processed_at
        FROM `{self.config.bigquery_project_id}.{self.config.dataset_id}.{self.config.table_id}`
        WHERE attachment_count > 0
        ORDER BY processed_at DESC
        LIMIT {limit}
        """
        
        try:
            results = list(self.bigquery_client.query(query).result())
            
            print(f"\n📋 Recent {len(results)} emails with attachments:")
            for row in results:
                subject = row.subject[:50] + "..." if len(row.subject) > 50 else row.subject
                print(f"\n  📧 {subject}")
                print(f"     From: {row.sender}")
                print(f"     Attachments: {row.successful_uploads}/{row.attachment_count} uploaded")
                
                if row.attachment_summary:
                    attachments = json.loads(row.attachment_summary)
                    for att in attachments[:3]:  # Show first 3 attachments
                        if att.get('gcs_url'):
                            print(f"     🔗 {att['filename']}: {att['gcs_url']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Query error: {e}")
            return []


class GmailProcessor:
    """Main processor for Gmail emails."""
    
    def __init__(self, config: Config):
        self.config = config
        self.auth_manager = AuthenticationManager(config)
        
        # Initialize services
        self.gmail_service = self.auth_manager.authenticate_gmail()
        self.bigquery_client = self.auth_manager.authenticate_bigquery()
        self.storage_client = self.auth_manager.authenticate_gcs()
        
        # Initialize managers
        self.gcs_manager = GCSManager(self.storage_client, config)
        self.email_parser = EmailParser(self.gmail_service, self.gcs_manager, config)
        self.bigquery_manager = BigQueryManager(self.bigquery_client, config)
        
        # Setup infrastructure
        self.bigquery_manager.create_table()
    
    def get_unread_emails(self, max_results: int = 100) -> List[EmailData]:
        """Fetch and parse unread emails."""
        try:
            results = self.gmail_service.users().messages().list(
                userId='me', q='is:unread', maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            print(f"📧 Found {len(messages)} unread emails")
            
            email_data = []
            
            for i, message in enumerate(messages, 1):
                print(f"\n[{i}/{len(messages)}] Processing message {message['id'][:8]}...")
                
                # Get full message
                msg = self.gmail_service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                # Parse email and process attachments
                parsed_email = self.email_parser.parse_email(msg)
                email_data.append(parsed_email)
                
            return email_data
            
        except Exception as error:
            print(f"❌ Error fetching emails: {error}")
            return []
    
    def process_unread_emails(self, max_results: int = 50):
        """Main processing function."""
        print("🚀 Starting Gmail to BigQuery processor with GCS attachments...\n")
        
        # Process emails
        emails = self.get_unread_emails(max_results)
        
        if emails:
            # Store in BigQuery
            self.bigquery_manager.store_emails(emails)
            
            # Show statistics
            self._show_processing_summary()
            
            print(f"\n✅ Processing completed successfully!")
        else:
            print("📭 No unread emails found.")
    
    def _show_processing_summary(self):
        """Display processing statistics."""
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        
        gcs_stats = self.gcs_manager.get_statistics()
        if 'error' not in gcs_stats:
            print(f"GCS Bucket ({self.config.gcs_bucket_name}):")
            print(f"  • Total files: {gcs_stats['total_files']}")
            print(f"  • Total size: {gcs_stats['total_size_mb']} MB")
            print(f"  • File types: {gcs_stats['file_types']}")
        
        # Show recent emails with attachments
        self.bigquery_manager.query_recent_emails_with_attachments(limit=3)


def main():
    """Main entry point."""
    config = Config()
    
    try:
        processor = GmailProcessor(config)
        processor.process_unread_emails(max_results=20)
        
    except KeyboardInterrupt:
        print("\n⏹ Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
