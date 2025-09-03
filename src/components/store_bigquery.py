def store_emails_in_bigquery(bigquery_client, table_ref, emails):
    """
    Store email data in BigQuery.

    Args:
        bigquery_client: Authenticated BigQuery client
        emails: List of parsed email dictionaries
    """
    if not emails:
        print("⚠ No emails to store")
        return

    # Prepare data for insertion
    rows_to_insert = []
    for email in emails:
        row = {
            "message_id": email["message_id"],
            "thread_id": email["thread_id"],
            "subject": email["subject"],
            "sender": email["sender"],
            "recipient": email["recipient"],
            "date_received": email["date_received"],
            "parsed_date": email["parsed_date"],
            "body_text": email["body_text"][:1000000] if email["body_text"] else None,
            "label_ids": email["label_ids"],
            "snippet": email["snippet"],
            "message_size": email["message_size"],
            "attachment_count": email["attachment_count"],
            "attachment_summary": email["attachment_summary"],
            "total_attachment_size": email["total_attachment_size"],
            "successful_uploads": email["successful_uploads"],
            "processed_at": email["processed_at"],
        }
        rows_to_insert.append(row)

    # Insert data
    errors = bigquery_client.insert_rows_json(table_ref, rows_to_insert)

    if errors:
        print(f"❌ BigQuery insertion errors: {errors}")
    else:
        total_attachments = sum(email["attachment_count"] for email in emails)
        total_successful = sum(email["successful_uploads"] for email in emails)

        print(f"✓ Stored {len(emails)} emails in BigQuery")
        if total_attachments > 0:
            print(
                f"  📎 {total_successful}/{total_attachments} attachments uploaded successfully"
            )
