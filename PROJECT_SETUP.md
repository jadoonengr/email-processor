# GCP Resource Setup Guide

This guide will walk you through the steps to set up the necessary Google Cloud Platform (GCP) resources. Follow these instructions carefully to get the project up and running in your own environment.

---

## Step 1: Project Setup

Before you begin, ensure you have the gcloud command-line tool installed and authenticated.

### 1.1: Define Environment Variables

First, we set up the core project variables. These variables are only meant for the CLI environment to set the GCP resources easily. These values should be same as defined in the `config.ini` file. We can customize these values too, but be sure to use unique names for resources like the bucket and project ID.

```bash
# Core Settings
export PROJECT_ID='email-management-system-96bc'
export REGION='us-central1'
export BQ_LOCATION='US'

# Service Accounts
export SERVICE_ACCOUNT_NAME="email-mgmt-dev-sa"
export DEPLOYMENT_SA_NAME="email-mgmt-deploy-dev-sa"
export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export DEPLOYMENT_SA_EMAIL="${DEPLOYMENT_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# BigQuery
export DATASET_NAME='idp'
export TABLE_NAME='gmail_raw_emails'

# Cloud Storage (globally unique names)
export BUCKET_NAME='gmail-attachments-bucket-96bc-2fba'
export NOTIFICATIONS_BUCKET='gmail-pub-sub-notifications'

# Pub/Sub
export PUBSUB_TOPIC='email-notifier-topic'
export PUBSUB_SUBSCRIPTION='email-notifier-sub'

# Cloud Functions
export FUNCTION_NAME='email-management-system'
export ENTRY_POINT='process_emails'
export SECRET_NAME='gmail-token'
export GMAIL_SCOPES='https://www.googleapis.com/auth/gmail.modify'
```

### 1.2: Enable Required APIs

Note: Better to enable services one-by-one.

```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### 1.3: Create Your GCP Project

```bash
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
```

Ensure that the **billing account** is enabled for this project.

---

## Step 2: Create Cloud Resources

### 2.1: BigQuery Table

Note: "Record" based BigQuery tables can only be created using a schema JSON file.

```bash
# Create dataset (if it doesn't exist)
bq mk --location=$BQ_LOCATION --dataset $PROJECT_ID:$DATASET_NAME

# Create schema.json file on local system using CLI
cat << 'EOF' > schema.json
[
  {
    "name": "message_id",
    "mode": "REQUIRED",
    "type": "STRING"
  },
  {
    "name": "thread_id",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "subject",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "sender",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "recipient",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "date_received",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "parsed_date",
    "mode": "NULLABLE",
    "type": "TIMESTAMP"
  },
  {
    "name": "body_text",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "label_ids",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "snippet",
    "mode": "NULLABLE",
    "type": "STRING"
  },
  {
    "name": "message_size",
    "mode": "NULLABLE",
    "type": "INTEGER"
  },
  {
    "name": "attachment_count",
    "mode": "NULLABLE",
    "type": "INTEGER"
  },
  {
    "name": "attachments_info",
    "mode": "REPEATED",
    "type": "RECORD",
    "fields": [
      {
        "name": "file_id",
        "mode": "NULLABLE",
        "type": "STRING"
      },
      {
        "name": "file_name",
        "mode": "NULLABLE",
        "type": "STRING"
      },
      {
        "name": "file_type",
        "mode": "NULLABLE",
        "type": "STRING"
      },
      {
        "name": "gcs_url",
        "mode": "NULLABLE",
        "type": "STRING"
      }
    ]
  },
  {
    "name": "processed_at",
    "mode": "NULLABLE",
    "type": "TIMESTAMP"
  }
]
EOF

# Create table with schema
bq mk --table \
--schema ./schema.json \
$PROJECT_ID:$DATASET_NAME.$TABLE_NAME
```

### 2.2: Cloud Storage Buckets

```bash
# Bucket for Raw Emails Storage
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION --default-storage-class=STANDARD --uniform-bucket-level-access


### 2.3: Pub/Sub Resources

```bash
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=$PUBSUB_TOPIC
```

### 2.4: Create Gmail API Credentials (<span style="color: red;">CRITICAL STEP</span>)

You can create OAuth client IDs and secrets through the Google Cloud Console. This is where you'd create credentials for web applications or installed applications where a user directly grants consent.


Process:

Step 1:
- Go to the Google Cloud Console.
- Navigate to APIs & Services > Credentials.
- Click Create Credentials and select OAuth client ID.
- Choose the application type as "Desktop app".
- After creation, you'll get a Client ID and Client Secret. Download your OAuth2 credentials from the same page as JSON file (Note: If not saved, the credentials cannot be retrieved later on)
- Place the JSON file in your **project's parent directory** named as "credentials.json".

Step 2:
- Go to the "Audience" tab and add your email ID under "Test users" category as it will ensure that you can use your gmail account to connect to GCP services.

Step 3:
- Next, under "Data Access" tab, click on "Add or remove scopes" and add:  
"https://www.googleapis.com/auth/gmail.modify"


### 2.5: Secret Manager

Once we get the Gmail authentication credentials, we need to run the Email Management System locally for the first time to get token.json file using credentials.json. Token file is automatically uploaded to the Secret File created during this step. Google Cloud Secret Manager is used to store the Gmail API tokens loaded using Python code.

```bash
gcloud secrets create $SECRET_NAME --replication-policy="automatic"
```

---

## Step 3: Create and Configure Service Accounts


### 3.1: Configure Gmail Push Service Account

You need to grant a specific, predefined Google Service Account the Pub/Sub Publisher role on your Google Cloud Project. Grant the Gmail Push Service Account permission to publish to your project's Pub/Sub topics.

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
```


### 3.2: Working Service Account

This service account is used for the normal execution of the Cloud Function. It contain minimal permissions to perform the operations.

```bash
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME     --display-name="Email Management System DEV Service Account"     --description="Service Account for Email Management System DEV Environment"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/storage.objectUser"

# Grant Storage Object Admin role directly on the target bucket
# NOTE: Due to GCS issues, Object Admin role alone is not enough for CF to work.
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/storage.bucketViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/cloudfunctions.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/pubsub.publisher

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/logging.logWriter

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/secretmanager.secretVersionAdder

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/cloudbuild.builds.editor"
```

### 3.3: Deployment Service Account

Deployment service account is a privileged account that has more permissions than normal accounts. It has access to several other GCP services like Cloud Build.

```bash
gcloud iam service-accounts create $DEPLOYMENT_SA_NAME     --display-name="Email Management System Deployment DEV Service Account"     --description="Service Account for Email Management System Deployment in DEV Environment"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$DEPLOYMENT_SA_EMAIL"     --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$DEPLOYMENT_SA_EMAIL"     --role="roles/storage.objectUser"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$DEPLOYMENT_SA_EMAIL     --role=roles/cloudfunctions.admin

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$DEPLOYMENT_SA_EMAIL     --role=roles/pubsub.admin

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$DEPLOYMENT_SA_EMAIL     --role=roles/logging.logWriter

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$DEPLOYMENT_SA_EMAIL     --role=roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$DEPLOYMENT_SA_EMAIL     --role=roles/iam.serviceAccountUser
```
