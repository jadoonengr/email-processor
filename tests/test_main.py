# import pytest
# import unittest.mock as mock
# import json
# import os
# import base64
# from datetime import datetime
# from main import process_emails

# # Mock data for Pub/Sub event and Gmail API responses
# MOCK_USER_ID = "jadoon.engr@gmail.com"
# MOCK_PUB_SUB_PAYLOAD = {
#     "message": {
#         "data": base64.b64encode(
#             json.dumps({"emailAddress": MOCK_USER_ID, "historyId": "123456"}).encode(
#                 "utf-8"
#             )
#         ).decode("utf-8")
#     }
# }

# # # --- Mock Gmail API Responses ---

# # # Response for users().messages().list()
# # MOCK_GMAIL_LIST_RESPONSE = {
# #     "messages": [
# #         {"id": "latest_message_id"},
# #     ]
# # }

# # # Response for users().messages().get() for an email with an attachment
# # MOCK_GMAIL_MESSAGE_WITH_ATTACHMENT = {
# #     "id": "latest_message_id",
# #     "snippet": "This is a test email with an attachment.",
# #     "internalDate": "1672531200000",  # Jan 1, 2023, in milliseconds
# #     "payload": {
# #         "headers": [
# #             {"name": "Subject", "value": "Test Email with Attachment"},
# #             {"name": "From", "value": "sender@example.com"},
# #         ],
# #         "parts": [
# #             {"mimeType": "text/plain", "body": {"size": 100}},
# #             {
# #                 "mimeType": "application/pdf",
# #                 "filename": "document.pdf",
# #                 "body": {"attachmentId": "mock_attachment_id", "size": 500},
# #             },
# #         ],
# #     },
# # }

# # # Response for users().messages().get() for an email with no attachment
# # MOCK_GMAIL_MESSAGE_NO_ATTACHMENT = {
# #     "id": "latest_message_id",
# #     "snippet": "This is a test email with no attachment.",
# #     "internalDate": "1672531200000",
# #     "payload": {
# #         "headers": [
# #             {"name": "Subject", "value": "Test Email with No Attachment"},
# #             {"name": "From", "value": "sender@example.com"},
# #         ],
# #         "parts": [
# #             {"mimeType": "text/plain", "body": {"size": 100}},
# #         ],
# #     },
# # }

# # # Response for users().messages().attachments().get()
# # MOCK_GMAIL_ATTACHMENT_DATA = {
# #     "data": base64.urlsafe_b64encode(b"this is the file content").decode("utf-8")
# # }

# # --- Pytest Fixtures ---


# @pytest.fixture
# def mock_cloud_event():
#     """Mocks the CloudEvent object for the Pub/Sub trigger."""
#     event = mock.Mock()
#     event.data = MOCK_PUB_SUB_PAYLOAD
#     return event


# @pytest.fixture(autouse=True)
# def set_env_vars(monkeypatch):
#     """Sets environment variables using monkeypatch."""
#     monkeypatch.setenv("APP_ENV", "dev")
#     with open("./token.json", "r") as token_file:
#         token_data = token_file.read()
#     monkeypatch.setenv("TOKEN_STRING", token_data)


# # --- Unit Tests ---


# # @mock.patch("main.build")
# # @mock.patch("main.default", return_value=(mock.Mock(), "test-project"))
# # @mock.patch("main.storage.Client")
# # @mock.patch("main.bigquery.Client")
# def test_process_email_with_attachment_success(
#     # mock_bigquery_client,
#     # mock_storage_client,
#     # mock_default,
#     # mock_build,
#     mock_cloud_event,
# ):
#     """Tests processing an email with a single attachment successfully."""
#     # # Set up mock Gmail API client responses
#     # mock_gmail_service = mock.Mock()
#     # mock_build.return_value = mock_gmail_service

#     # # Mock the list() method to return a message ID
#     # mock_gmail_service.users().messages().list().execute.return_value = MOCK_GMAIL_LIST_RESPONSE
#     # # Mock the get() method to return the email with an attachment
#     # mock_gmail_service.users().messages().get().execute.return_value = MOCK_GMAIL_MESSAGE_WITH_ATTACHMENT
#     # # Mock the attachments().get() method to return the attachment data
#     # mock_gmail_service.users().messages().attachments().get().execute.return_value = MOCK_GMAIL_ATTACHMENT_DATA

#     # # Set up mock storage client responses
#     # mock_bucket = mock.Mock()
#     # mock_blob = mock.Mock()
#     # mock_storage_client.bucket.return_value = mock_bucket
#     # mock_bucket.blob.return_value = mock_blob

#     # Run the function
#     process_emails(mock_cloud_event)

#     # Assertions
#     # # Verify Gmail API calls
#     # mock_gmail_service.users().messages().list.assert_called_once_with(userId=MOCK_USER_ID, maxResults=1)
#     # mock_gmail_service.users().messages().get.assert_called_once_with(userId=MOCK_USER_ID, id='latest_message_id', format='full')
#     # mock_gmail_service.users().messages().attachments().get.assert_called_once_with(
#     #     userId=MOCK_USER_ID, messageId='latest_message_id', id='mock_attachment_id'
#     # )

#     # # Verify attachment upload to GCS
#     # mock_storage_client.bucket.assert_called_once_with('test_bucket')
#     # mock_blob.upload_from_string.assert_called_once()

#     # # Verify BigQuery insertion
#     # mock_bigquery_client.return_value.dataset().table().insert_rows_json.assert_called_once()

#     # # Verify the inserted data contains correct attachment info
#     # inserted_rows = mock_bigquery_client.return_value.dataset().table().insert_rows_json.call_args[0][1][0]
#     # attachments_info = json.loads(inserted_rows['attachments_info'])
#     # assert len(attachments_info) == 1
#     # assert attachments_info[0]['filename'] == 'document.pdf'
#     # assert attachments_info[0]['size_bytes'] == 24
#     # assert 'gs://test_bucket' in attachments_info[0]['gcs_path']
#     # assert inserted_rows['message_id'] == 'latest_message_id'
#     assert 1 == 1


# # @mock.patch("main.build")
# # @mock.patch("main.default", return_value=(mock.Mock(), "test-project"))
# # @mock.patch("main.storage.Client")
# # @mock.patch("main.bigquery.Client")
# # def test_process_email_no_attachment_success(
# #     mock_bigquery_client,
# #     mock_storage_client,
# #     mock_default,
# #     mock_build,
# #     mock_cloud_event
# # ):
# #     """Tests processing an email with no attachments successfully."""
# #     # Set up mock Gmail API client responses
# #     mock_gmail_service = mock.Mock()
# #     mock_build.return_value = mock_gmail_service
# #     mock_gmail_service.users().messages().list().execute.return_value = MOCK_GMAIL_LIST_RESPONSE
# #     mock_gmail_service.users().messages().get().execute.return_value = MOCK_GMAIL_MESSAGE_NO_ATTACHMENT

# #     # Run the function
# #     process_email(mock_cloud_event)

# #     # Assertions
# #     # Verify Gmail API calls
# #     mock_gmail_service.users().messages().list.assert_called_once()
# #     mock_gmail_service.users().messages().get.assert_called_once()
# #     mock_gmail_service.users().messages().attachments().get.assert_not_called() # Crucial: no attachment call

# #     # Verify BigQuery insertion and attachment info is empty
# #     mock_bigquery_client.return_value.dataset().table().insert_rows_json.assert_called_once()
# #     inserted_rows = mock_bigquery_client.return_value.dataset().table().insert_rows_json.call_args[0][1][0]
# #     attachments_info = json.loads(inserted_rows['attachments_info'])
# #     assert len(attachments_info) == 0

# # @mock.patch("main.build")
# # @mock.patch("main.default", return_value=(mock.Mock(), "test-project"))
# # def test_no_messages_found(
# #     mock_default,
# #     mock_build,
# #     mock_cloud_event
# # ):
# #     """Tests the function's behavior when no messages are returned by Gmail."""
# #     # Set up mock Gmail API to return no messages
# #     mock_gmail_service = mock.Mock()
# #     mock_build.return_value = mock_gmail_service
# #     mock_gmail_service.users().messages().list().execute.return_value = {'messages': []}

# #     # Run the function (it should return without error)
# #     try:
# #         process_email(mock_cloud_event)
# #     except Exception as e:
# #         pytest.fail(f"Function raised an unexpected exception: {e}")

# #     # Assert that no other calls were made
# #     mock_gmail_service.users().messages().get.assert_not_called()

# # @mock.patch("main.build")
# # def test_exception_handling(mock_build, mock_cloud_event):
# #     """Tests that the function handles unexpected exceptions gracefully."""
# #     # Mock the build call to raise an exception
# #     mock_build.side_effect = Exception("Mocked API error")

# #     # The function should catch the exception and print an error message, but not raise one
# #     with mock.patch("builtins.print") as mock_print:
# #         process_email(mock_cloud_event)
# #         mock_print.assert_called_with("An unexpected error occurred: Mocked API error")
