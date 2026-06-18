FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mailgun_extract.py load_to_bigquery.py transform.py run_pipeline.py ./

CMD ["python", "run_pipeline.py", "--days", "1"]
