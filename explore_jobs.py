import json

with open("mailgun_logs_2026-05-27.json") as f:
    records = json.load(f)

for record in records:
    uv = record.get("user-variables")
    if uv and isinstance(uv, str):
        uv = json.loads(uv)
    if uv and "jobs" in uv:
        jobs = uv["jobs"]
        if isinstance(jobs, str):
            jobs = json.loads(jobs)
        if jobs:
            print("Keys inside a job object:")
            for key in jobs[0].keys():
                print(f"  {key}")
            break