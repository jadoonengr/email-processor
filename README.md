# Gmail Email Processor

A robust Python application for processing Gmail emails, extracting attachments, and storing data in Google Cloud services. Built specifically for Google Cloud Functions with comprehensive email management capabilities.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Platform-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🚀 Tech Stack Summary

| **Category** | **Technology** | **Purpose** |
|--------------|----------------|-------------|
| **Language** | Python 3.11 | Primary programming language |
| **Compute** | Google Cloud Functions Gen 2 | Serverless email processing |
| **Database** | Google BigQuery | Raw email storage |
| **Storage** | Google Cloud Storage | Email attachments storage |
| **Messaging** | Google Cloud Pub/Sub | Event-driven notifications |
| **Security** | Google Secret Manager | OAuth token storage |
| **Authentication** | OAuth 2.0 + Gmail API | Gmail access |
| **Scheduling** | Google Cloud Scheduler | Watch renewal automation |
| **CI/CD** | Google Cloud Build | Automated deployment |
| **Version Control** | GitHub | Code repository |
| **Monitoring** | Cloud Logging/Monitoring | Observability |

## Key Python Libraries

| **Library** | **Purpose** |
|-------------|-------------|
| `functions-framework` | Cloud Functions runtime |
| `google-api-python-client` | Gmail API integration |
| `google-auth` | Google authentication |
| `google-cloud-bigquery` | Database operations |
| `google-cloud-storage` | Storage operations |
| `google-cloud-pubsub` | Message handling |
| `google-cloud-secret-manager` | Credential management |

## Architecture Pattern
**Event-Driven Serverless**: Gmail → Pub/Sub → Cloud Functions → Business Logic
- **Gmail API Integration**: Secure OAuth2 authentication with Gmail
- **Email Processing**: Extract email content, headers, and metadata  
- **Attachment Management**: Download and upload attachments to Google Cloud Storage
- **BigQuery Storage**: Store processed email data in BigQuery for analytics
- **Cloud Function Ready**: Designed to run as serverless Google Cloud Functions
- **Error Handling**: Comprehensive error handling and logging
- **Scalable Architecture**: Efficient design for maintainability and testing

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Cloud Function Deployment](#cloud-function-deployment)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

```
Gmail API → Email Processing → Attachment Storage (GCS) → Data Storage (BigQuery)
```

The application follows a modular architecture:

- **Authentication Layer**: Handles OAuth2 for Gmail, BigQuery, and GCS
- **Processing Layer**: Extracts email content and attachments
- **Storage Layer**: Manages data persistence in Google Cloud services
- **Orchestration Layer**: Coordinates the entire workflow

## 📋 Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Google Cloud Project with billing enabled
- Gmail API enabled
- BigQuery API enabled  
- Cloud Storage API enabled
- Service account with appropriate permissions

### Required Google Cloud APIs

```bash
gcloud services enable gmail.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gmail-processor.git
   cd gmail-processor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Google Cloud credentials**
   ```bash
   # Download your OAuth2 credentials from Google Cloud Console
   # Place the JSON file in your project directory
   ```

## ⚙️ Configuration

### 1. Create Configuration File

Create `src/config.py`:

```python
config = {
    "development": {
        "PROJECT_ID": "your-gcp-project-id",
        "GCS_BUCKET_NAME": "your-storage-bucket",
        "BIGQUERY_DATASET": "your_dataset",
        "BIGQUERY_TABLE": "emails",
        "CREDENTIALS_FILE": "path/to/credentials.json",
        "GMAIL_SCOPES": "https://www.googleapis.com/auth/gmail.readonly"
    },
    "production": {
        # Production configuration
    }
}

ENV = "development"  # or "production"
```

### 2. BigQuery Schema

Create your BigQuery table with this schema:

```sql
CREATE TABLE `your-project.your_dataset.emails` (
  message_id STRING,
  thread_id STRING,
  subject STRING,
  sender STRING,
  recipient STRING,
  date_received STRING,
  parsed_date TIMESTAMP,
  body_text STRING,
  label_ids STRING,
  snippet STRING,
  message_size INTEGER,
  attachment_count INTEGER,
  attachments_info JSON,
  processed_at TIMESTAMP
);
```

### 3. Google Cloud Storage

Create a storage bucket for attachments:

```bash
gsutil mb gs://your-attachment-bucket
```

## 🎯 Usage

### Local Development

#### Function-Based Approach
```python
from src.components.auth_services import authenticate_gmail
from src.components.process_emails import list_unread_emails, read_email

# Initialize services
gmail_service = authenticate_gmail()
emails = list_unread_emails(gmail_service, max_results=10)

# Process emails
for email in emails:
    processed_email = read_email(gmail_service, email)
    print(f"Processed: {processed_email['subject']}")
```

#### Class-Based Approach (Recommended)
```python
from src.gmail_processor import GmailProcessor
from src.config import config, ENV

# Initialize processor
processor = GmailProcessor(config[ENV])

# Process all unread emails
summary = processor.process_all_unread_emails(max_results=50)
print(f"Processed: {summary['processed']}, Failed: {summary['failed']}")
```

### Standalone Script

```python
#!/usr/bin/env python3
import sys
from src.gmail_processor import GmailProcessor
from src.config import config, ENV

def main():
    try:
        processor = GmailProcessor(config[ENV])
        summary = processor.process_all_unread_emails()
        
        print("📊 Processing Summary:")
        print(f"   ✅ Total emails: {summary['total']}")
        print(f"   ✅ Successfully processed: {summary['processed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        
        return 0 if summary['failed'] == 0 else 1
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## ☁️ Cloud Function Deployment

### 1. Prepare Deployment Files

**requirements.txt**
```
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
google-cloud-bigquery>=3.0.0
google-cloud-storage>=2.0.0
functions-framework>=3.0.0
```

**main.py** (Entry point)
```python
import functions_framework
from src.gmail_processor import GmailProcessor
from src.config import config, ENV

@functions_framework.cloud_event
def process_gmail_emails(cloud_event):
    """Cloud Function entry point."""
    processor = GmailProcessor(config[ENV])
    summary = processor.process_all_unread_emails()
    return {"success": True, "summary": summary}
```

### 2. Deploy to Google Cloud Functions

```bash
# Deploy the function
gcloud functions deploy process-gmail-emails \
    --gen2 \
    --runtime=python39 \
    --region=us-central1 \
    --source=. \
    --entry-point=process_gmail_emails \
    --trigger-topic=gmail-notifications \
    --memory=512MB \
    --timeout=540s
```

### 3. Set up Gmail Push Notifications

```bash
# Create Pub/Sub topic
gcloud pubsub topics create gmail-notifications

# Set up Gmail watch (replace with your email)
curl -X POST \
  "https://gmail.googleapis.com/gmail/v1/users/me/watch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topicName": "projects/YOUR_PROJECT_ID/topics/gmail-notifications",
    "labelIds": ["UNREAD"]
  }'
```

## 📚 API Reference

### GmailProcessor Class

#### Constructor
```python
GmailProcessor(config: Dict[str, Any])
```
Initialize the processor with configuration dictionary.

#### Methods

##### `process_all_unread_emails(max_results: int = 100) -> Dict[str, int]`
Process all unread emails and return processing summary.

##### `process_email(email_ref: Dict[str, str]) -> Optional[Dict[str, Any]]`
Process a single email and return structured data.

##### `get_unread_emails(max_results: int = 100) -> List[Dict[str, Any]]`
Fetch unread email references from Gmail.

##### `store_email_in_bigquery(email_data: Dict[str, Any]) -> bool`
Store processed email data in BigQuery.

### Configuration Parameters

| Parameter | Description | Required |
|-----------|-------------|----------|
| `PROJECT_ID` | Google Cloud Project ID | Yes |
| `GCS_BUCKET_NAME` | Cloud Storage bucket name | Yes |
| `BIGQUERY_DATASET` | BigQuery dataset name | Yes |
| `BIGQUERY_TABLE` | BigQuery table name | Yes |
| `CREDENTIALS_FILE` | OAuth2 credentials file path | Yes |
| `GMAIL_SCOPES` | Gmail API scopes | Yes |

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── test_auth_services.py
├── test_process_emails.py
├── test_storage.py
├── test_gmail_processor.py
└── conftest.py
```

### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from src.gmail_processor import GmailProcessor

def test_gmail_processor_initialization():
    config = {
        "PROJECT_ID": "test-project",
        "GCS_BUCKET_NAME": "test-bucket",
        # ... other config
    }
    
    with patch('src.gmail_processor.GmailProcessor._initialize_services'):
        processor = GmailProcessor(config)
        assert processor.config == config
```

## 📊 Monitoring and Logging

### Cloud Logging

The application uses structured logging that integrates with Google Cloud Logging:

```python
import logging
logger = logging.getLogger(__name__)

# Log levels used:
logger.info("Processing started")      # General information
logger.warning("No attachments found") # Warnings
logger.error("Failed to upload file")  # Errors
```

### Monitoring Metrics

Track these key metrics in Cloud Monitoring:
- Email processing rate
- Success/failure ratios  
- Attachment upload success
- BigQuery insertion errors
- Function execution time

## 🚨 Error Handling

The application includes comprehensive error handling:

- **Authentication Errors**: Automatic token refresh and re-authentication
- **API Rate Limits**: Built-in retry logic with exponential backoff
- **Network Issues**: Connection timeout and retry mechanisms
- **Storage Errors**: Graceful handling of upload failures
- **Data Validation**: Input validation and sanitization

## 🔒 Security Considerations

- **OAuth2 Tokens**: Securely stored and automatically refreshed
- **IAM Permissions**: Principle of least privilege
- **Data Encryption**: All data encrypted in transit and at rest
- **Sensitive Data**: No email content logged in production
- **Access Controls**: Proper BigQuery and GCS access controls

### Required IAM Roles

```bash
# Service account permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:your-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:your-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"
```

## 🚀 Performance Optimization

- **Batch Processing**: Process multiple emails in single BigQuery insert
- **Parallel Uploads**: Concurrent attachment uploads to GCS
- **Memory Management**: Efficient handling of large attachments
- **Connection Pooling**: Reuse HTTP connections for API calls
- **Caching**: Cache authentication tokens and service objects

## 🐛 Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: Gmail authentication failed
Solution: Check credentials file path and OAuth2 setup
```

#### BigQuery Insert Errors
```
Error: BigQuery insertion errors: [...]
Solution: Verify table schema matches data structure
```

#### Storage Upload Failures
```
Error: Failed to upload attachment
Solution: Check bucket permissions and file size limits
```

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Roadmap

- [ ] **Batch Processing**: Process emails in configurable batches
- [ ] **Retry Logic**: Exponential backoff for failed operations
- [ ] **Webhook Support**: Direct webhook integration for real-time processing
- [ ] **Email Filtering**: Advanced filtering and labeling capabilities
- [ ] **Analytics Dashboard**: Built-in reporting and analytics
- [ ] **Multi-User Support**: Support for multiple Gmail accounts
- [ ] **Attachment Processing**: OCR and content extraction from attachments

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/gmail-processor.git
cd gmail-processor

# Install development dependencies  
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
python -m pytest
```

### Code Style

We use Black for code formatting and flake8 for linting:

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Cloud Platform for robust cloud services
- Gmail API for comprehensive email access
- The Python community for excellent libraries

## 📞 Support

- **Documentation**: Check the [Wiki](../../wiki) for detailed guides
- **Issues**: Report bugs and request features in [Issues](../../issues)
- **Discussions**: Join community discussions in [Discussions](../../discussions)
- **Email**: For private inquiries: support@yourproject.com

---

**Made with ❤️ by [Aamir M. Khan](https://github.com/jadoonengr)**

*If this project helped you, please consider giving it a ⭐!*
