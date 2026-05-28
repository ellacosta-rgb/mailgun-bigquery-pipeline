import requests
import json
import os
from datetime import datetime, timedelta, timezone

# Compute yesterday's date window in RFC 2822 format
today = datetime.now(timezone.utc)
yesterday = today - timedelta(days=1)

start = "Wed, 27 May 2026 00:00:00 -0000"
end = "Thu, 28 May 2026 00:00:00 -0000"

print(f"Fetching logs from {start} to {end}")

# API credentials
api_key = os.environ.get("MAILGUN_API_KEY")

# Paginate through all results
all_records = []
token = None
page = 1

while True:
    print(f"Fetching page {page}...")

    pagination = {"sort": "timestamp:asc", "limit": 100}
    if token:
        pagination["token"] = token

    response = requests.post(
        "https://api.mailgun.net/v1/analytics/logs",
        auth=("api", api_key),
        json={
            "start": start,
            "end": end,
            "filter": {
                "AND": [
                    {
                        "attribute": "domain",
                        "comparator": "=",
                        "values": [
                            {
                                "label": "peratonjobalerts.com",
                                "value": "peratonjobalerts.com"
                            }
                        ]
                    }
                ]
            },
            "events": ["accepted", "delivered", "failed", "opened", "clicked", "unsubscribed", "complained"],
            "include_subaccounts": True,
            "include_totals": True,
            "pagination": pagination
        }
    )
    print(response.json())
    data = response.json()
    items = data.get("items", [])
    all_records.extend(items)

    print(f"Page {page}: got {len(items)} records (total so far: {len(all_records)})")

    token = data.get("pagination", {}).get("next")
    if not token:
        break

    page += 1

# Save to JSON file
output_filename = f"mailgun_logs_{yesterday.strftime('%Y-%m-%d')}.json"
with open(output_filename, "w") as f:
    json.dump(all_records, f, indent=2)

print(f"Done! {len(all_records)} records saved to {output_filename}")