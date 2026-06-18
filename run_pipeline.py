#!/usr/bin/env python3
"""Extract Mailgun logs and load them into BigQuery."""

import subprocess
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_DAYS = 1


def run_date(date_str: str) -> None:
    print(f"\n{'=' * 60}\nProcessing {date_str}\n{'=' * 60}")
    subprocess.run([sys.executable, "mailgun_extract.py", date_str], check=True)
    subprocess.run([sys.executable, "load_to_bigquery.py", date_str], check=True)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] != "--days":
        run_date(sys.argv[1])
        return

    days = DEFAULT_DAYS
    if len(sys.argv) > 2 and sys.argv[1] == "--days":
        days = int(sys.argv[2])

    today = datetime.now(timezone.utc).date()
    for offset in range(days, 0, -1):
        date_str = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        run_date(date_str)


if __name__ == "__main__":
    main()
