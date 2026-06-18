import requests
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential


def parse_user_variables(uv):
    if not uv:
        return {}
    if isinstance(uv, str):
        try:
            return json.loads(uv)
        except json.JSONDecodeError:
            return {}
    return uv


def classify_email_type(record, uv):
    subject = (record.get("message") or {}).get("headers", {}).get("subject", "") or ""
    if "Welcome" in subject and "Job Alert" in subject:
        return "signup"
    if "job_count" in uv or subject.startswith("Your Weekly Job Alert"):
        return "alert"
    return "other"


def is_unsubscribe_click(record):
    return (
        record.get("event") == "clicked"
        and "unsubscribe" in (record.get("url") or "").lower()
    )


# Use passed date or default to yesterday
if len(sys.argv) > 1:
    target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(tzinfo=timezone.utc)
else:
    target_date = datetime.now(timezone.utc) - timedelta(days=1)

start = target_date.strftime("%a, %d %b %Y 00:00:00 -0000")
end = (target_date + timedelta(days=1)).strftime("%a, %d %b %Y 00:00:00 -0000")

print(f"Fetching logs from {start} to {end}")

# API credentials
api_key = os.environ.get("MAILGUN_API_KEY")
print(f"Key starts with: {api_key[:8]}")
if not api_key:
    print("Error: MAILGUN_API_KEY environment variable is not set", file=sys.stderr)
    sys.exit(1)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
def fetch_page(pagination):
    response = requests.post(
        "https://api.mailgun.net/v1/analytics/logs",
        auth=("api", api_key),
        json={
            "start": start,
            "end": end,
            "include_subaccounts": True,
            "include_totals": True,
            "pagination": pagination
        },
        timeout=60,
    )
    if response.status_code == 429:
        print("Rate limited, retrying...")
        raise Exception("Rate limited")
    if response.status_code == 401:
        print("Error: Invalid API key")
        sys.exit(1)
    if response.status_code >= 500 or not response.text.strip():
        print(f"Mailgun API error {response.status_code}, retrying...")
        raise Exception(f"Bad response: {response.status_code}")
    try:
        response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Invalid JSON from Mailgun (status {response.status_code}), retrying...")
        raise Exception("Invalid JSON response")
    return response

# Paginate through all results
all_records = []
token = None
page = 1

while True:
    print(f"Fetching page {page}...")

    pagination = {"sort": "timestamp:asc", "limit": 100}
    if token:
        pagination["token"] = token

    response = fetch_page(pagination)
    data = response.json()
    items = data.get("items", [])
    all_records.extend(items)

    print(f"Page {page}: got {len(items)} records (total so far: {len(all_records)})")

    token = data.get("pagination", {}).get("next")
    if not token:
        break

    page += 1

# Summary
event_counts = Counter(record.get("event") for record in all_records)
non_empty_user_vars = sum(1 for record in all_records if record.get("user-variables") not in [None, {}, ""])
email_type_counts = Counter()
unsubscribe_clicks = 0

for record in all_records:
    uv = parse_user_variables(record.get("user-variables"))
    email_type_counts[classify_email_type(record, uv)] += 1
    if is_unsubscribe_click(record):
        unsubscribe_clicks += 1

print("\n--- Summary ---")
print(f"Time range: {start} to {end}")
print(f"Total records: {len(all_records)}")
print("\nBreakdown by event type:")
event_order = ["accepted", "delivered", "opened", "clicked", "failed"]
for event in event_order:
    if event in event_counts:
        print(f"  {event}: {event_counts[event]}")
print(f"\nRecords with non-empty user-variables: {non_empty_user_vars} / {len(all_records)}")
print("\nBreakdown by email type:")
for email_type in ["signup", "alert", "other"]:
    if email_type in email_type_counts:
        print(f"  {email_type}: {email_type_counts[email_type]}")
print(f"\nUnsubscribe clicks: {unsubscribe_clicks}")
print("--- End Summary ---\n")

# Save to JSON file
output_filename = f"mailgun_logs_{target_date.strftime('%Y-%m-%d')}.json"
with open(output_filename, "w") as f:
    json.dump(all_records, f, indent=2)

print(f"Done! {len(all_records)} records saved to {output_filename}")