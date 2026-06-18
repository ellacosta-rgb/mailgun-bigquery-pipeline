# mailgun-bigquery-pipeline

Pulls Mailgun Analytics Logs and loads them into BigQuery for dashboard use.

## Pipeline

1. `mailgun_extract.py` — fetches one day of logs from Mailgun
2. `transform.py` — classifies email types and flattens job data
3. `load_to_bigquery.py` — merges into `hireclix.mailgun_analytics.email_events`

Or run all steps at once:

```bash
# Single day
python3 run_pipeline.py 2026-06-03

# Yesterday only (default for daily automation)
python3 run_pipeline.py

# Backfill a date range
python3 run_pipeline.py --days 30
```

## Local setup

```bash
pip install -r requirements.txt
export MAILGUN_API_KEY="your-key"
gcloud auth application-default login
python3 run_pipeline.py
```

## Daily automation on GCP

The recommended setup is a **Cloud Run Job** triggered by **Cloud Scheduler** every day at 4:00 AM. Each run processes yesterday's data.

### 1. Store the Mailgun API key

```bash
echo -n "your-mailgun-api-key" | gcloud secrets create mailgun-api-key --data-file=-
```

### 2. Build and deploy the job

```bash
PROJECT_ID=hireclix
REGION=us-central1
IMAGE=gcr.io/$PROJECT_ID/mailgun-pipeline

gcloud builds submit --tag $IMAGE

gcloud run jobs create mailgun-pipeline \
  --image $IMAGE \
  --region $REGION \
  --set-secrets MAILGUN_API_KEY=mailgun-api-key:latest \
  --service-account YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com
```

The service account needs:
- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`
- `roles/secretmanager.secretAccessor`

### 3. Schedule it daily at 4 AM

```bash
PROJECT_ID=hireclix
REGION=us-central1
SA_EMAIL=mailgun-pipeline@$PROJECT_ID.iam.gserviceaccount.com

gcloud scheduler jobs create http mailgun-pipeline-daily \
  --location $REGION \
  --schedule "0 4 * * *" \
  --time-zone "America/New_York" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/mailgun-pipeline:run" \
  --http-method POST \
  --oauth-service-account-email $SA_EMAIL

gcloud run jobs add-iam-policy-binding mailgun-pipeline \
  --region $REGION \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker"
```

If you already created a weekly scheduler job, update it instead:

```bash
gcloud scheduler jobs update http mailgun-pipeline-weekly \
  --location $REGION \
  --schedule "0 4 * * *" \
  --time-zone "America/New_York"
```

Change `--time-zone` if you want 4 AM in a different timezone (e.g. `UTC`).

### 4. Test manually

```bash
gcloud run jobs execute mailgun-pipeline --region $REGION
```

## Notes

- Log JSON files (`mailgun_logs_*.json`) are temporary local artifacts — they are not committed to git.
- Re-running the pipeline for a date is safe; the BigQuery MERGE updates existing rows.
- For backfills, run locally: `python3 run_pipeline.py --days 30`
