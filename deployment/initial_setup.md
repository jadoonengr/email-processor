# Step 1: Create Big Query Table
# =====================================================

# Set your variables
PROJECT_ID="alpine-comfort-470817-s8"
DATASET_NAME="idp"
TABLE_NAME="gmail_raw_emails"
LOCATION="us-central1"

# Create dataset first (if it doesn't exist)
gcloud config set project $PROJECT_ID

bq mk \
    --location=$LOCATION \
    --dataset \
    $PROJECT_ID:$DATASET_NAME

# Create table with schema
bq mk \
    --table \
    $PROJECT_ID:$DATASET_NAME.$TABLE_NAME \
    message_id:STRING:REQUIRED,thread_id:STRING,subject:STRING,sender:STRING,recipient:STRING,date_received:STRING,parsed_date:TIMESTAMP,body_text:STRING,label_ids:STRING,snippet:STRING,message_size:INTEGER,attachment_count:INTEGER,attachments_info:RECORD:REPEATED,attachments_info.file_id:STRING,attachments_info.file_name:STRING,attachments_info.file_type:STRING,attachments_info.gcs_url:STRING,processed_at:TIMESTAMP

# Step 2: Create Cloud Storage Buckets
# =====================================================
# Bucket for Raw Emails Storage
gcloud storage buckets create gs://gmail-attachments-bucket-2fba \
    --location=us-central1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Bucket for Pub/Sub Notifications Messages
gcloud storage buckets create gs://gmail-pub-sub-notifications \
    --location=us-central1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access


# Step 3: Create Service Account
# =====================================================
# Set your project ID
SERVICE_ACCOUNT_NAME="email-notifier-dev-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Set the project
gcloud config set project $PROJECT_ID

# Create the service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Email Notifier Development Service Account" \
    --description="Service account for email notification system development"

# Assign BigQuery Data Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataEditor"

# Assign Cloud Build Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudbuild.builds.editor"

# Assign Cloud Functions Developer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudfunctions.developer"

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectUser"

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/pubsub.editor"