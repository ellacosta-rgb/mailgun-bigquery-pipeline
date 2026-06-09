import json

with open("mailgun_logs_2026-06-01.json") as f:
    records =  json.load(f)

for record in records[:5]:
    print("tags: ", record.get("tags"))
    print("message: ", record.get("message"))
    print("envelope: ", record.get("envelope"))
    print("--------------------------------")