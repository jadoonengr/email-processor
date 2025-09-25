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

# Cloud Storage
export BUCKET_NAME='gmail-attachments-bucket-2fba'
export NOTIFICATIONS_BUCKET='gmail-pub-sub-notifications'

# Pub/Sub
export PUBSUB_TOPIC='email-notifier-topic'
export PUBSUB_SUBSCRIPTION='email-notifier-sub'

# Cloud Functions
export FUNCTION_NAME='email-management-system'
export ENTRY_POINT='process_emails'
export SECRET_NAME='gmail-token'
```

### 1.2: Enable Required APIs

```bash
gcloud services enable \
bigquery.googleapis.com     \
storage.googleapis.com     \
cloudfunctions.googleapis.com     \
pubsub.googleapis.com     \
gmail.googleapis.com     \
cloudbuild.googleapis.com     \
secretmanager.googleapis.com     \
artifactregistry.googleapis.com     \
cloudresourcemanager.googleapis.com
```

### 1.3: Create Your GCP Project

```bash
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
```

---

## Step 2: Create Cloud Resources

### 2.1: BigQuery Table

```bash
# Create dataset (if it doesn't exist)
bq mk     --location=$BQ_LOCATION     --dataset     $PROJECT_ID:$DATASET_NAME

# Create table with schema
bq mk     --table     $PROJECT_ID:$DATASET_NAME.$TABLE_NAME     message_id:STRING:REQUIRED,     thread_id:STRING,     subject:STRING,     sender:STRING,     recipient:STRING,     date_received:STRING,     parsed_date:TIMESTAMP,     body_text:STRING,     label_ids:STRING,     snippet:STRING,     message_size:INTEGER,     attachment_count:INTEGER,     attachments_info:RECORD:REPEATED,     attachments_info.file_id:STRING,     attachments_info.file_name:STRING,     attachments_info.file_type:STRING,     attachments_info.gcs_url:STRING,     processed_at:TIMESTAMP
```

### 2.2: Cloud Storage Buckets

```bash
# Bucket for Raw Emails Storage
gcloud storage buckets create gs://$BUCKET_NAME     --location=$REGION     --default-storage-class=STANDARD     --uniform-bucket-level-access

# Bucket for Pub/Sub Notifications Messages
gcloud storage buckets create gs://$NOTIFICATIONS_BUCKET     --location=$REGION     --default-storage-class=STANDARD     --uniform-bucket-level-access
```

### 2.3: Pub/Sub Resources

```bash
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=$PUBSUB_TOPIC
```

### 2.4: Create Gmail API Credentials

You can create OAuth client IDs and secrets through the Google Cloud Console. This is where you'd create credentials for web applications or installed applications where a user directly grants consent.


Process:

- Go to the Google Cloud Console.
- Navigate to APIs & Services > Credentials.
- Click Create Credentials and select OAuth client ID.
- Choose the application type as "Desktop app".
- After creation, you'll get a Client ID and Client Secret. Download your OAuth2 credentials from the same page as JSON file (Note: If not saved, the credentials cannot be retrieved later on)
- Place the JSON file in your project's parent directory named as "credentials.json".


### 2.5: Secret Manager

Google Cloud Secret Manager is used to store the Gmail API tokens downloaded from OAuth step.

```bash
gcloud secrets create $SECRET_NAME --replication-policy="automatic"
gcloud secrets versions add $SECRET_NAME --data-file="./token.json"
```

---

## Step 3: Create and Configure Service Accounts

### 3.1: Working Service Account

This service account is used for the normal execution of the Cloud Function. It contain minimal permissions to perform the operations.

```bash
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME     --display-name="Email Management System DEV Service Account"     --description="Service Account for Email Management System DEV Environment"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/storage.objectUser"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/cloudfunctions.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/pubsub.publisher

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/logging.logWriter

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding $PROJECT_ID     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL     --role=roles/secretmanager.secretVersionAdder

gcloud projects add-iam-policy-binding $PROJECT_ID     --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL"     --role="roles/cloudbuild.builds.editor"
```

### 3.2: Deployment Service Account

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
