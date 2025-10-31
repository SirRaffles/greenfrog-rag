# Website Scraper for The Matcha Initiative
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scrape_matcha.py .
COPY sync_to_anythingllm.py .
COPY run_scraper.sh .
COPY entrypoint.sh .

# Make scripts executable
RUN chmod +x run_scraper.sh entrypoint.sh

# Create directories
RUN mkdir -p /data /logs /data/state

# Add cron job (runs daily at 2 AM)
RUN echo "0 2 * * * cd /app && ./run_scraper.sh >> /logs/scraper-cron.log 2>&1" | crontab -

# Expose no ports (background service)

# Health check (verify cron is running)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep cron || exit 1

# Entrypoint starts cron and allows manual runs
ENTRYPOINT ["./entrypoint.sh"]
CMD ["cron", "-f"]
