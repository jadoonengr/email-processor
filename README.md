# Email Management and Processing System

A Python-based serverless application built using Google Cloud Functions with comprehensive email management capabilities. It processes emails by automatically extracting Gmail messages and storing structured data in BigQuery. Moreover, the email attachments (if any) are saved in Cloud Storage.


![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Platform-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Cloud Build](https://img.shields.io/badge/build-passing-green.svg)

---

## 🚀 Tech Stack Summary

| **Category** | **Technology** | **Purpose** |
|--------------|----------------|-------------|
| **Language** | Python 3.13 | Primary programming language |
| **Compute** | Google Cloud Functions Gen 2 | Serverless email processing |
| **Database** | Google BigQuery | Raw email storage |
| **Storage** | Google Cloud Storage | Email attachments storage |
| **Messaging** | Google Cloud Pub/Sub | Event-driven notifications |
| **Security** | Google Secret Manager | OAuth token storage |
| **Authentication** | OAuth 2.0 + Gmail API | Gmail access |
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

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Initial Resource Setup](#setup)
- [Usage](#usage)
- [Cloud Function Deployment](#cloud-function-deployment)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)


---

## 🏗️ Architecture

The application follows a modular architecture:

- **Authentication Layer**: Handles OAuth2 for Gmail, BigQuery, and GCS
- **Processing Layer**: Extracts email content and attachments
- **Storage Layer**: Manages data persistence in Google Cloud services
- **Orchestration Layer**: Coordinates the entire workflow

```
Gmail API → Pub/Sub Topic → Cloud Function → Email Text + Email Attachments
                                                 ↓              ↓
                                              BigQuery    Cloud Storage
```

Key features of the architecture are:

- **Event-Driven Serverless**: Gmail → Pub/Sub → Cloud Functions → Data Storage
- **Gmail API Integration**: Secure OAuth2 authentication with Gmail
- **Email Processing**: Extract email content, headers, and metadata  
- **Attachment Management**: Download and upload attachments to Google Cloud Storage
- **BigQuery Storage**: Store processed email data in BigQuery for analytics
- **Cloud Function Ready**: Designed to run as serverless Google Cloud Functions
- **Error Handling**: Comprehensive error handling and logging
- **Scalable Architecture**: Efficient design for maintainability and testing

---

## 📋 Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Google Cloud Project with billing enabled
- Gmail API enabled
- Cloud Functions, BigQuery, and Cloud Storage APIs enabled
- Service account with appropriate permissions

---

## ⚙️ Configuration

### 1. Create Configuration File

Populate `src/config.ini` with desired project resource information. Same information will be used later to create resources using `gcloud` utility. Sample settings for the `DEV` environment are shown below.

```python
[dev]
PROJECT_ID = alpine-comfort-470817-s8
EMAIL_ID = aamirjadoon001@gmail.com
CREDENTIALS_FILE = credentials.json
SECRET_NAME = gmail-token
GMAIL_SCOPES = https://www.googleapis.com/auth/gmail.modify
GCS_BUCKET_NAME = gmail-attachments-bucket-2fba
BIGQUERY_DATASET = idp
BIGQUERY_TABLE = gmail_raw_emails
PUBSUB_TOPIC = email-notifier
SERVICE_ACCOUNT = email-notifier-dev-sa@alpine-comfort-470817-s8. iam.gserviceaccount.com
```

### 2. BigQuery Schema

For the BigQuery table, we need to define the schema. The following information is saved in the BigQuery table. Any changes to this schema needs changes in the relevant code. A sample SQL query is shown below to create this table. But we create it using `gcloud` command later.

```sql
CREATE TABLE `alpine-comfort-470817-s8.idp.gmail_raw_emails` (
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

### 3. Initial Project Setup

Once we define the initial parameters above, the next step is to create those resources and then deploy the source code. Following resources are to be created:

- Create project
- BigQuery table
- Cloud Storage bucket
- Cloud Pub/Sub Topic and Subscription
- Secret key on Cloud Secret Manager
- Working and deployment service accounts with relevant permissions

This is quite involved process and we have created a separate page to go over all the required steps. At the end of these steps, we will be able to run our code locally (using Cloud resources).

GCP Resource Setup Guide: [PROJECT_SETUP.md](PROJECT_SETUP.md)

---

## 🛠️ Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jadoonengr/email-management-system.git
   cd email-management-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   source env/Scripts/activate      # On Windows
   <!-- source env/bin/activate      # On Linux -->
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

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
├── test_email_processor.py
└── conftest.py
```


---

## ☁️ Cloud Function Deployment


### Manual Deployment

```bash
gcloud functions deploy $FUNCTION_NAME 
    --gen2     
    --runtime=python312    
    --region=$REGION 
    --source=.     
    --entry-point=$ENTRY_POINT     --trigger-topic=$PUBSUB_TOPIC     --memory=512MB     
    --timeout=540s     
```

### Test the Deployment

```bash
gcloud pubsub topics publish $PUBSUB_TOPIC  --message '{"emailAddress": "jadoon.engr@gmail.com", "messageId": "abc123"}'
```

You should now have a fully functional email processing system running in your Google Cloud Project!



### CI/CD Pipeline Implementation using Cloud Build



## 📚 API Reference

#### Methods

##### `process_all_unread_emails(max_results: int = 100) -> Dict[str, int]`
Process all unread emails and return processing summary.

##### `process_email(email_ref: Dict[str, str]) -> Optional[Dict[str, Any]]`
Process a single email and return structured data.

##### `get_unread_emails(max_results: int = 100) -> List[Dict[str, Any]]`
Fetch unread email references from Gmail.

##### `store_email_in_bigquery(email_data: Dict[str, Any]) -> bool`
Store processed email data in BigQuery.


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

### Monitoring Metrics (Future Enhancements)

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
