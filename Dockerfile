
# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .

# Create a virtual environment and install dependencies into it
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production Image ----
FROM python:3.11-slim

# Set environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy app code
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Streamlit doesn't like running as root by default; fix that
ENV STREAMLIT_SERVER_HEADLESS=true

# Command to run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
