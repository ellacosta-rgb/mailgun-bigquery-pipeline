import json
import pandas as pd

# Load the raw data
with open("mailgun_logs_2026-05-27.json") as f:
    records = json.load(f)

print(f"Loaded {len(records)} records")

def parse_json_list(value):
    """Parse a JSON-encoded list string into a Python list."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except:
        return []

def parse_user_variables(uv):
    """Parse user-variables field."""
    if not uv:
        return {}
    if isinstance(uv, str):
        try:
            return json.loads(uv)
        except:
            return {}
    return uv

def get_job_fields(jobs_raw, job_index):
    """Extract fields for a specific job by index."""
    if not jobs_raw:
        return {}
    if isinstance(jobs_raw, str):
        try:
            jobs = json.loads(jobs_raw)
        except:
            return {}
    else:
        jobs = jobs_raw
    
    if not isinstance(jobs, list) or job_index >= len(jobs):
        return {}
    
    job = jobs[job_index]
    return {
        f"job_{job_index + 1}_title": job.get("title", ""),
        f"job_{job_index + 1}_url": job.get("job_url", ""),
        f"job_{job_index + 1}_location": job.get("location", ""),
        f"job_{job_index + 1}_clearance": job.get("clearance", ""),
        f"job_{job_index + 1}_workplace": job.get("workplace", ""),
        f"job_{job_index + 1}_pay_range": job.get("pay_range", ""),
    }

rows = []
for record in records:
    uv = parse_user_variables(record.get("user-variables"))
    jobs_raw = uv.get("jobs")

    row = {
        # Core event fields
        "id": record.get("id"),
        "event": record.get("event"),
        "event_timestamp": record.get("@timestamp"),
        "domain": record.get("domain", {}).get("name") if isinstance(record.get("domain"), dict) else record.get("domain"),        "recipient": record.get("recipient"),
        "recipient_domain": record.get("recipient-domain"),
        "severity": record.get("severity"),
        "log_level": record.get("log-level"),

        # User variable fields
        "alert_id": uv.get("alert_id"),
        "email": uv.get("email"),
        "frequency": uv.get("frequency"),
        "job_count": int(uv.get("job_count")) if uv.get("job_count") else None,
        "search_summary": uv.get("search_summary"),
        "category": parse_json_list(uv.get("category")),
        "clearance": parse_json_list(uv.get("clearance")),
        "keyword": parse_json_list(uv.get("keyword")),
        "location": parse_json_list(uv.get("location")),
        "position_type": parse_json_list(uv.get("position_type")),
        "workplace": parse_json_list(uv.get("workplace")),

        # Full payload
        "payload": json.dumps(record),
    }

    # Add job fields for up to 5 jobs
    #for i in range(5):
     #   row.update(get_job_fields(jobs_raw, i))

    rows.append(row)

df = pd.DataFrame(rows)

print(f"\nDataframe shape: {df.shape}")
print("\nColumns:")
for col in df.columns:
    print(f"  {col}")

print("\nSample row:")
print(df.iloc[0])

# Check job_count values
print("\nJob count value counts:")
print(df['job_count'].value_counts())


