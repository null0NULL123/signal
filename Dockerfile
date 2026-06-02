# ---- Build stage (core) ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (gcc needed for sqlite-vec compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env for easy copy
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Build stage (UI) ----
FROM builder AS builder-ui

COPY requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt \
    # Remove unnecessary files to reduce image size
    && find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null \
    && find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null \
    && find /app/.venv -type d -name "test" -exec rm -rf {} + 2>/dev/null \
    && rm -rf /app/.venv/lib/python*/site-packages/*/examples 2>/dev/null \
    && rm -rf /app/.venv/lib/python*/site-packages/pyarrow/tests 2>/dev/null \
    && rm -rf /app/.venv/lib/python*/site-packages/pandas/tests 2>/dev/null \
    && rm -rf /app/.venv/lib/python*/site-packages/numpy/tests 2>/dev/null

# ---- Runtime base (shared by core & ui) ----
FROM python:3.12-slim AS runtime-base

WORKDIR /app

COPY sift/ sift/
COPY pages/ pages/
RUN mkdir -p /app/workspaces

# ---- Runtime stage (core / CLI) ----
FROM runtime-base AS core

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python3", "sift/cli.py"]
CMD ["run"]

# ---- Runtime stage (UI) ----
FROM runtime-base AS ui

COPY --from=builder-ui /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY .streamlit/ .streamlit/
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "sift/app.py"]
CMD ["--server.address=0.0.0.0"]
