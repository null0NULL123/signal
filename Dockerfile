FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for sqlite-vec
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY cli.py config.py models.py pipeline.py workspace.py app.py ./
COPY sources/ sources/
COPY processors/ processors/
COPY channels/ channels/
COPY storage/ storage/
COPY prompts/ prompts/
COPY pages/ pages/
COPY feeds.json .

# Create directories for volumes
RUN mkdir -p /app/output /app/knowledge /app/workspaces

# Default: run weekly digest
ENTRYPOINT ["python3", "cli.py"]
CMD ["run"]
