FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY baseline_fits ./baseline_fits
COPY data ./data

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "long_sus.api:app", "--host", "0.0.0.0", "--port", "8000"]
