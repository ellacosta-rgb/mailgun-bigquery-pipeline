import requests
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

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
        }
    )
    if response.status_code == 429:
        print("Rate limited, retrying...")
        raise Exception("Rate limited")
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

#Summary of the data
from collections import Counter

event_counts = Counter(record.get("event") for record in all_records)
non_empty_user_vars = sum(1 for record in all_records if record.get("user-variables") not in [None, {}, ""])
print("\n--- Summary ---")
print(f"Time range: {start} to {end}")
print(f"Total records: {len(all_records)}")
print("\nBreakdown by event type:")
for event, count in sorted(event_counts.items()):
    print(f"  {event}: {count}")
print(f"\nRecords with non-empty user-variables: {non_empty_user_vars} / {len(all_records)}")
print("--- End Summary ---\n")

# Save to JSON file
output_filename = f"mailgun_logs_{target_date.strftime('%Y-%m-%d')}.json"
with open(output_filename, "w") as f:
    json.dump(all_records, f, indent=2)

print(f"Done! {len(all_records)} records saved to {output_filename}")