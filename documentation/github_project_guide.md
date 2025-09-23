# 📧 Email Processor - Gmail to BigQuery Pipeline

A serverless email processing system that automatically extracts Gmail emails, processes attachments, and stores structured data in BigQuery using Google Cloud Functions.

## 🏗️ Architecture Overview

```
Gmail API → Cloud Function → BigQuery + Cloud Storage
    ↑             ↓              ↓
Pub/Sub ←    Attachments    Structured
Topic        to GCS         Email Data
```

**Key Components:**
- **Gmail API**: Fetches unread emails with push notifications
- **Cloud Function**: Processes emails and extracts data
- **BigQuery**: Stores structured email metadata
- **Cloud Storage**: Stores email attachments
- **Pub/Sub**: Triggers processing via Gmail notifications
- **Secret Manager**: Securely stores Gmail credentials

## ✨ Features

- 🔄 **Real-time Processing**: Automatic email processing via Gmail push notifications
- 📎 **Attachment Handling**: Extracts and stores attachments in Cloud Storage
- 🗃️ **Structured Storage**: Stores email metadata in BigQuery for analytics
- 🔒 **Secure Authentication**: Uses service accounts and Secret Manager
- 📊 **Scalable**: Serverless architecture handles variable email volumes
- 🚨 **Error Handling**: Comprehensive logging and error management

## 🚀 Quick Start

### Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Gmail API credentials (`token.json`)
- Python 3.12+ for local development

### 1️⃣ Setup Environment Variables

```bash
# Core Settings
export PROJECT_ID='your-project-id'
export REGION='us-central1'
export BQ_LOCATION='US'

# Service Accounts
export SERVICE_ACCOUNT_NAME="email-mgmt-dev-sa"
export DEPLOYMENT_SA_NAME="email-mgmt-deploy-dev-sa"

# Resources
export DATASET_NAME='idp'
export TABLE_NAME='gmail_raw_emails'
export BUCKET_NAME='gmail-attachments-bucket-2fba'
export PUBSUB_TOPIC='email-notifier'
export FUNCTION_NAME='email-management-system'
export SECRET_NAME='gmail-token'
```

### 2️⃣ Enable Required APIs

```bash
# Enable all necessary Google Cloud services
gcloud services enable bigquery.googleapis.com \
                      storage.googleapis.com \
                      cloudfunctions.googleapis.com \
                      pubsub.googleapis.com \
                      gmail.googleapis.com \
                      cloudbuild.googleapis.com \
                      secretmanager.googleapis.com \
                      artifactregistry.googleapis.com
```

### 3️⃣ Create BigQuery Resources

```bash
# Create dataset
bq mk --location=$BQ_LOCATION --dataset $PROJECT_ID:$DATASET_NAME

# Create table with predefined schema
bq mk --table $PROJECT_ID:$DATASET_NAME.$TABLE_NAME \
  message_id:STRING:REQUIRED,\
  thread_id:STRING,\
  subject:STRING,\
  sender:STRING,\
  recipient:STRING,\
  date_received:STRING,\
  parsed_date:TIMESTAMP,\
  body_text:STRING,\
  label_ids:STRING,\
  snippet:STRING,\
  message_size:INTEGER,\
  attachment_count:INTEGER,\
  attachments_info:RECORD:REPEATED,\
  attachments_info.file_id:STRING,\
  attachments_info.file_name:STRING,\
  attachments_info.file_type:STRING,\
  attachments_info.gcs_url:STRING,\
  processed_at:TIMESTAMP
```

### 4️⃣ Create Cloud Storage Buckets

```bash
# Main bucket for email attachments
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --uniform-bucket-level-access

# Optional: Bucket for Pub/Sub notification logs
gcloud storage buckets create gs://gmail-pub-sub-notifications \
    --location=$REGION \
    --uniform-bucket-level-access
```

### 5️⃣ Setup Pub/Sub Resources

```bash
# Create topic and subscription
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create email-notifier-sub --topic=$PUBSUB_TOPIC

# Grant Gmail API permission to publish
gcloud pubsub topics add-iam-policy-binding $PUBSUB_TOPIC \
    --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
    --role=roles/pubsub.publisher
```

### 6️⃣ Store Gmail Credentials

```bash
# Create secret and upload your Gmail token
gcloud secrets create $SECRET_NAME --replication-policy="automatic"
gcloud secrets versions add $SECRET_NAME --data-file="./token.json"
```

### 7️⃣ Create Service Accounts

#### Working Service Account
```bash
# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Email Management System Service Account"

# Set service account email
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Assign required roles
for ROLE in \
    "roles/bigquery.dataEditor" \
    "roles/storage.objectUser" \
    "roles/cloudfunctions.developer" \
    "roles/pubsub.publisher" \
    "roles/logging.logWriter" \
    "roles/secretmanager.secretAccessor" \
    "roles/secretmanager.secretVersionAdder"
do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="$ROLE"
done
```

#### Deployment Service Account
```bash
# Create deployment service account
gcloud iam service-accounts create $DEPLOYMENT_SA_NAME \
    --display-name="Email Management Deployment Service Account"

DEPLOYMENT_SA_EMAIL="$DEPLOYMENT_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Assign deployment roles
for ROLE in \
    "roles/cloudfunctions.admin" \
    "roles/pubsub.admin" \
    "roles/iam.serviceAccountUser" \
    "roles/secretmanager.secretAccessor"
do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$DEPLOYMENT_SA_EMAIL" \
        --role="$ROLE"
done
```

### 8️⃣ Deploy the Function

```bash
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=process_emails \
    --trigger-topic=$PUBSUB_TOPIC \
    --service-account=$SERVICE_ACCOUNT_EMAIL \
    --memory=512MB \
    --timeout=60s \
    --region=$REGION
```

### 9️⃣ Test the Deployment

```bash
# Test with a sample message
gcloud pubsub topics publish $PUBSUB_TOPIC \
  --message='{"historyId": "12345", "emailAddress": "your-email@gmail.com"}'
```

## 📊 Data Schema

### BigQuery Table Structure

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | STRING (Required) | Unique Gmail message ID |
| `thread_id` | STRING | Gmail conversation thread ID |
| `subject` | STRING | Email subject line |
| `sender` | STRING | Sender email address |
| `recipient` | STRING | Recipient email address |
| `date_received` | STRING | Original email date string |
| `parsed_date` | TIMESTAMP | Parsed timestamp |
| `body_text` | STRING | Email body content |
| `label_ids` | STRING | Gmail label IDs (JSON) |
| `snippet` | STRING | Email snippet preview |
| `message_size` | INTEGER | Email size in bytes |
| `attachment_count` | INTEGER | Number of attachments |
| `attachments_info` | RECORD (Repeated) | Attachment details |
| `processed_at` | TIMESTAMP | Processing timestamp |

### Attachment Information Schema

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | STRING | Gmail attachment ID |
| `file_name` | STRING | Original filename |
| `file_type` | STRING | MIME type |
| `gcs_url` | STRING | Cloud Storage download URL |

## 🔧 Configuration

### Environment Configuration

Create a `src/config.py` file:

```python
config = {
    "DEV": {
        "PROJECT_ID": "your-project-id",
        "GCS_BUCKET_NAME": "your-bucket-name",
        "BIGQUERY_DATASET": "idp",
        "BIGQUERY_TABLE": "gmail_raw_emails",
        "PUBSUB_TOPIC": "email-notifier"
    }
}

ENV = "DEV"  # or "PROD"
```

## 🧪 Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

```bash
# Test Gmail authentication
python -m src.components.auth_services

# Test email processing
python -m src.components.process_emails
```

## 📁 Project Structure

```
email-processor/
├── src/
│   ├── components/
│   │   ├── auth_services.py      # Authentication services
│   │   ├── process_emails.py     # Email processing logic
│   │   ├── store_bigquery.py     # BigQuery operations
│   │   ├── store_gcs.py          # Cloud Storage operations
│   │   └── setup_gmail_notifications.py
│   ├── utils/
│   │   └── file_utils.py         # Utility functions
│   └── config.py                 # Configuration settings
├── tests/                        # Unit tests
├── main.py                       # Cloud Function entry point
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚨 Troubleshooting

### Common Issues

**1. Authentication Errors**
- Verify service account has correct roles
- Check Secret Manager contains valid Gmail token
- Ensure Gmail API is enabled

**2. Permission Denied**
- Confirm service account email in IAM bindings
- Verify bucket and dataset permissions
- Check Pub/Sub topic permissions

**3. Function Timeout**
- Increase memory allocation for large email volumes
- Adjust timeout settings based on processing needs

**4. BigQuery Errors**
- Verify dataset exists and is accessible
- Check table schema matches data structure
- Ensure proper data types in inserts

### Monitoring

- **Cloud Functions Logs**: `gcloud functions logs read $FUNCTION_NAME`
- **BigQuery Query History**: Check BigQuery console for successful inserts
- **Cloud Storage**: Verify attachments are being uploaded
- **Pub/Sub Monitoring**: Check message acknowledgment rates

## 🔐 Security Best Practices

- ✅ Use service accounts with minimal required permissions
- ✅ Store sensitive credentials in Secret Manager
- ✅ Enable audit logging for all services
- ✅ Regularly rotate service account keys
- ✅ Use VPC-native resources when possible

## 📈 Scaling Considerations

- **Email Volume**: Function auto-scales based on Pub/Sub messages
- **Storage Costs**: Set up lifecycle policies for old attachments
- **BigQuery Costs**: Partition tables by date for large datasets
- **Rate Limits**: Gmail API has quotas - implement exponential backoff

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation
- Review Google Cloud Function logs

---

**Built with ❤️ using Google Cloud Platform**