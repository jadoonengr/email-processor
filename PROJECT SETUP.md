
# Step 1: Enable GCP Services
# =====================================================
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com

# Step 2: Create Environment Variables
# =====================================================
# Core Settings
PROJECT_ID='alpine-comfort-470817-s8'
# "email-management-system-fd34"
REGION='us-central1'
BQ_LOCATION='US'

# Service accounts
SERVICE_ACCOUNT_NAME="email-mgmt-dev-sa"
SERVICE_ACCOUNT_EMAIL: "${DEPLOYMENT_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOYMENT_SA_NAME="email-mgmt-deploy-dev-sa"
DEPLOYMENT_SA_EMAIL="${DEPLOYMENT_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# BigQuery
DATASET_NAME: 'idp'
TABLE_NAME: 'gmail_raw_emails'

# Cloud Storage
BUCKET_NAME: 'gmail-attachments-bucket-2fba'

# Pub/Sub
PUBSUB_TOPIC: 'email-notifier'
PUBSUB_SUBSCRIPTION: 'email-notifier-sub'

# Cloud Functions
FUNCTION_NAME: 'email-management-system'
ENTRY_POINT: 'process_emails'
SECRET_NAME: 'gmail-token'

# Step 2: Create Project
# =====================================================
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Step 3: Create Big Query Table
# =====================================================
# Create dataset first (if it doesn't exist)
bq mk \
    --location=$LOCATION \
    --dataset \
    $PROJECT_ID:$DATASET_NAME

# Create table with schema
bq mk \
    --table \
    $PROJECT_ID:$DATASET_NAME.$TABLE_NAME \
    message_id:STRING:REQUIRED,thread_id:STRING,subject:STRING,sender:STRING,recipient:STRING,date_received:STRING,parsed_date:TIMESTAMP,body_text:STRING,label_ids:STRING,snippet:STRING,message_size:INTEGER,attachment_count:INTEGER,attachments_info:RECORD:REPEATED,attachments_info.file_id:STRING,attachments_info.file_name:STRING,attachments_info.file_type:STRING,attachments_info.gcs_url:STRING,processed_at:TIMESTAMP

# Step 4: Create Cloud Storage Buckets
# =====================================================
# Bucket for Raw Emails Storage
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Bucket for Pub/Sub Notifications Messages
gcloud storage buckets create gs://gmail-pub-sub-notifications \
    --location=$REGION \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Step 5: Create Pub/Sub Resources
# =====================================================
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=$PUBSUB_TOPIC

# Step 6: Create Google Secrets from Token File
# =====================================================
gcloud secrets create $SECRET_NAME --replication-policy="automatic"
gcloud secrets versions add $SECRET_NAME --data-file="./token.json"

# Step 7: Create Working Service Account
# =====================================================
# Create Service Account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Email Management System DEV Service Account" \
    --description="Service Account for Email Management System DEV Environment"

# Assign BigQuery Data Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataEditor"

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectUser"

# Assign Cloud Functions Developer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudfunctions.developer"

# Assign Pub/Sub Publisher role
gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
     --role=roles/pubsub.publisher

# Assign Cloud Logging Log Writer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
    --role=roles/logging.logWriter

# Assign Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
    --role=roles/secretmanager.secretAccessor
# Assign Secret Manager Secret Version Adder role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
    --role=roles/secretmanager.secretVersionAdder

# Assign Cloud Build Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudbuild.builds.editor"


# Step 8: Create Deployment Service Account
# =====================================================
# Create Service Account
gcloud iam service-accounts create $DEPLOY_SA_NAME \
    --display-name="Email Management System Deployment DEV Service Account" \
    --description="Service Account for Email Management System Deployment in DEV Environment"
    
# Assign BigQuery Data Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$DEPLOY_SA_EMAIL" \
    --role="roles/bigquery.dataEditor"

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$DEPLOY_SA_EMAIL" \
    --role="roles/storage.objectUser"

# Assign Cloud Functions Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID\
    --member=serviceAccount:$DEPLOY_SA_EMAIL \
    --role=roles/cloudfunctions.admin

# Assign Pub/Sub Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member=serviceAccount:$DEPLOY_SA_EMAIL \
     --role=roles/pubsub.admin

# Assign Cloud Logging Log Writer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$DEPLOY_SA_EMAIL \
    --role=roles/logging.logWriter

# Assign Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$DEPLOY_SA_EMAIL \
    --role=roles/secretmanager.secretAccessor

# Grant Service Account User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$DEPLOY_SA_EMAIL \
    --role=roles/iam.serviceAccountUser
    
# Step 9: Deploy Code
# =====================================================
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=$ENTRY_POINT \
    --trigger-topic=$PUBSUB_TOPIC \
    --memory=512MB \
    --timeout=60s \
    --region=$REGION


# Step 10: Test Deployment
# =====================================================
gcloud pubsub topics publish $PUBSUB_TOPIC \
  --message '{"emailAddress": "jadoon.engr@gmail.com", "messageId": "abc123"}'
