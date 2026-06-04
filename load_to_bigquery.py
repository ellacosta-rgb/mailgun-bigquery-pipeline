import json
import pandas as pd
import sys
from datetime import datetime, timezone, timedelta
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

#Configure BigQuery client
PROJECT_ID = "hireclix-cdn"
DATASET_ID = "mailgun_analytics"
TABLE_ID = "email_events"


# Use passed date or default to yesterday
if len(sys.argv) > 1:
    target_date = sys.argv[1]
else:
    target_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

input_filename = f"mailgun_logs_{target_date}.json"
print(f"Loading {input_filename}")

#Initialize BigQuery client
client = bigquery.Client(project=PROJECT_ID)

#Full table reference
table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

print(f"Target table: {table_ref}")
print("BigQuery client initialized")

# Define BigQuery schema
schema = [
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("event", "STRING"),
    bigquery.SchemaField("event_timestamp", "TIMESTAMP"),
    bigquery.SchemaField("domain", "STRING"),
    bigquery.SchemaField("recipient", "STRING"),
    bigquery.SchemaField("recipient_domain", "STRING"),
    bigquery.SchemaField("severity", "STRING"),
    bigquery.SchemaField("log_level", "STRING"),
    bigquery.SchemaField("alert_id", "STRING"),
    bigquery.SchemaField("email", "STRING"),
    bigquery.SchemaField("frequency", "STRING"),
    bigquery.SchemaField("job_count", "INTEGER"),
    bigquery.SchemaField("search_summary", "STRING"),
    bigquery.SchemaField("category", "STRING", mode="REPEATED"),
    bigquery.SchemaField("clearance", "STRING", mode="REPEATED"),
    bigquery.SchemaField("keyword", "STRING", mode="REPEATED"),
    bigquery.SchemaField("location", "STRING", mode="REPEATED"),
    bigquery.SchemaField("position_type", "STRING", mode="REPEATED"),
    bigquery.SchemaField("workplace", "STRING", mode="REPEATED"),
    bigquery.SchemaField("payload", "STRING"),
    bigquery.SchemaField("job_1_title", "STRING"),
    bigquery.SchemaField("job_1_url", "STRING"),
    bigquery.SchemaField("job_1_location", "STRING"),
    bigquery.SchemaField("job_1_clearance", "STRING"),
    bigquery.SchemaField("job_1_workplace", "STRING"),
    bigquery.SchemaField("job_1_pay_range", "STRING"),
    bigquery.SchemaField("job_2_title", "STRING"),
    bigquery.SchemaField("job_2_url", "STRING"),
    bigquery.SchemaField("job_2_location", "STRING"),
    bigquery.SchemaField("job_2_clearance", "STRING"),
    bigquery.SchemaField("job_2_workplace", "STRING"),
    bigquery.SchemaField("job_2_pay_range", "STRING"),
    bigquery.SchemaField("job_3_title", "STRING"),
    bigquery.SchemaField("job_3_url", "STRING"),
    bigquery.SchemaField("job_3_location", "STRING"),
    bigquery.SchemaField("job_3_clearance", "STRING"),
    bigquery.SchemaField("job_3_workplace", "STRING"),
    bigquery.SchemaField("job_3_pay_range", "STRING"),
    bigquery.SchemaField("job_4_title", "STRING"),
    bigquery.SchemaField("job_4_url", "STRING"),
    bigquery.SchemaField("job_4_location", "STRING"),
    bigquery.SchemaField("job_4_clearance", "STRING"),
    bigquery.SchemaField("job_4_workplace", "STRING"),
    bigquery.SchemaField("job_4_pay_range", "STRING"),
    bigquery.SchemaField("job_5_title", "STRING"),
    bigquery.SchemaField("job_5_url", "STRING"),
    bigquery.SchemaField("job_5_location", "STRING"),
    bigquery.SchemaField("job_5_clearance", "STRING"),
    bigquery.SchemaField("job_5_workplace", "STRING"),
    bigquery.SchemaField("job_5_pay_range", "STRING"),
]

print("Schema defined successfully")
print(f"Total fields: {len(schema)}")

# Create table with partitioning and clustering
table = bigquery.Table(table_ref, schema=schema)

# Partition by event date
table.time_partitioning = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.DAY,
    field="event_timestamp"
)

# Cluster by event type and domain
table.clustering_fields = ["event", "domain"]

# Create the table (won't fail if it already exists)
table = client.create_table(table, exists_ok=True)
print(f"Table {table_ref} created successfully")
print(f"Partitioned by: event_timestamp")
print(f"Clustered by: event, domain")

# Load and transform the data
from transform import df, target_date as transform_date

# Write to BigQuery using MERGE for idempotency
print(f"\nWriting {len(df)} records to BigQuery...")

# First write to a temporary staging table
staging_table_ref = f"{PROJECT_ID}.{DATASET_ID}.email_events_staging"

job_config = bigquery.LoadJobConfig(
    schema=schema,
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

job = client.load_table_from_dataframe(df, staging_table_ref, job_config=job_config)
job.result()
print(f"Loaded {job.output_rows} rows to staging table")

# Now MERGE from staging into production, deduplicating on id
merge_query = f"""
MERGE `{PROJECT_ID}.{DATASET_ID}.email_events` T
USING `{staging_table_ref}` S
ON T.id = S.id AND T.event = S.event
WHEN NOT MATCHED THEN
  INSERT ROW
"""

print("Running MERGE into production table...")
query_job = client.query(merge_query)
query_job.result()
print(f"MERGE complete!")

# Clean up staging table
client.delete_table(staging_table_ref)
print("Staging table cleaned up")

# Final row count
count_query = f"SELECT COUNT(*) as total FROM `{PROJECT_ID}.{DATASET_ID}.email_events`"
count_job = client.query(count_query)
result = list(count_job.result())
print(f"\nTotal rows in production table: {result[0].total}")

# Write to BigQuery
print(f"\nWriting {len(df)} records to BigQuery...")
job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
job.result()  # Wait for the job to complete

print(f"Successfully loaded {job.output_rows} rows to {table_ref}")