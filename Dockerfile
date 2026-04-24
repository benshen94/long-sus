FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY baseline_fits ./baseline_fits
COPY data ./data

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "long_sus.api:app", "--host", "0.0.0.0", "--port", "8000"]
