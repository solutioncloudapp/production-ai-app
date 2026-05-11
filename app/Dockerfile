# Dockerfile for the main application.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY app/ ./app/
COPY evaluation/ ./evaluation/
COPY observability/ ./observability/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Install Python dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .[ml]

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
