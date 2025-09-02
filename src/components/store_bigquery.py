
def store_emails_in_bigquery(bigquery_client, table_ref, emails):
    """
    Store email data in BigQuery.
    
    Args:
        bigquery_client: Authenticated BigQuery client
        emails: List of parsed email dictionaries
    """
    if not emails:
        print("No emails to store")
        return
    
    
    # Prepare data for insertion
    rows_to_insert = []
    for email in emails:
        row = {
            'message_id': email['message_id'],
            'thread_id': email['thread_id'],
            'subject': email['subject'],
            'sender': email['sender'],
            'recipient': email['recipient'],
            'date_received': email['date_received'],
            'parsed_date': email['parsed_date'],
            'body_text': email['body_text'][:1000000] if email['body_text'] else None,  # Truncate if too long
            'label_ids': email['label_ids'],
            'snippet': email['snippet'],
            'message_size': email['message_size'],
            'processed_at': email['processed_at']
        }
        rows_to_insert.append(row)
    
    # Insert data
    errors = bigquery_client.insert_rows_json(table_ref, rows_to_insert)
    
    if errors:
        print(f"Errors occurred while inserting data: {errors}")
    else:
        print(f"Successfully inserted {len(rows_to_insert)} emails into BigQuery")
