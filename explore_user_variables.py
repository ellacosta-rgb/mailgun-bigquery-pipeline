import json

with open("mailgun_logs_2026-05-27.json") as f:
    records = json.load(f)

# Collect all unique user-variable keys
all_keys = set()
for record in records:
    uv = record.get("user-variables")
    if uv and uv not in [{}, "", None]:
        if isinstance(uv, str):
            uv = json.loads(uv)
        all_keys.update(uv.keys())

print("User-variable keys found:")
for key in sorted(all_keys):
    print(f"  {key}")