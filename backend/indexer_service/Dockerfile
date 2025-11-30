FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('punkt_tab')"

# Copy shared module
COPY shared/ ./shared/

# Copy indexer service
COPY indexer_service/ ./indexer_service/

WORKDIR /app/indexer_service

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('redis://redis:6379'); r.ping()" || exit 1

# Run the indexer
CMD ["python", "indexer.py", "--batch"]
