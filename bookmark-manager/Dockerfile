FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Claude CLI
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    cron \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Copy requirements (with service prefix for root context)
COPY bookmark-manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and shared library
COPY bookmark-manager/src/ ./src/
COPY bookmark-manager/scripts/ ./scripts/
COPY shared/ ./shared/

# Create data directory
RUN mkdir -p /app/data /app/data/backups

# Setup cron for daily backups and feed jobs
RUN (echo "0 2 * * * /app/scripts/backup_cron.sh"; \
     echo "0 */2 * * * cd /app && /usr/local/bin/python scripts/feed_refresh.py >> /var/log/feed_refresh.log 2>&1"; \
     echo "0 * * * * cd /app && /usr/local/bin/python scripts/feed_cleanup.py >> /var/log/feed_cleanup.log 2>&1") | crontab -

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["sh", "-c", "cron && uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
