#!/bin/bash
set -e

echo "🚀 Starting EchoSearch Backend..."

# Wait for Elasticsearch if ELASTICSEARCH_HOST is set
if [ -n "$ELASTICSEARCH_HOST" ]; then
    echo "⏳ Waiting for Elasticsearch at $ELASTICSEARCH_HOST:${ELASTICSEARCH_PORT:-9200}..."
    until nc -z "$ELASTICSEARCH_HOST" "${ELASTICSEARCH_PORT:-9200}" 2>/dev/null; do
        echo "   Elasticsearch not ready, retrying in 2s..."
        sleep 2
    done
    echo "✅ Elasticsearch is available"
fi

# Wait for Redis if REDIS_HOST is set
if [ -n "$REDIS_HOST" ]; then
    echo "⏳ Waiting for Redis at $REDIS_HOST:${REDIS_PORT:-6379}..."
    until nc -z "$REDIS_HOST" "${REDIS_PORT:-6379}" 2>/dev/null; do
        echo "   Redis not ready, retrying in 2s..."
        sleep 2
    done
    echo "✅ Redis is available"
fi

# Wait for PostgreSQL if POSTGRES_HOST is set
if [ -n "$POSTGRES_HOST" ]; then
    echo "⏳ Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" 2>/dev/null; do
        echo "   PostgreSQL not ready, retrying in 2s..."
        sleep 2
    done
    echo "✅ PostgreSQL is available"
    
    # Run database migrations/schema
    echo "📦 Initializing database schema..."
    python -c "
import psycopg2
import os

try:
    conn = psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'localhost'),
        port=os.environ.get('POSTGRES_PORT', 5432),
        database=os.environ.get('POSTGRES_DB', 'searchdb'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', 'postgres123')
    )
    cur = conn.cursor()
    
    # Read and execute schema
    if os.path.exists('schema.sql'):
        with open('schema.sql', 'r') as f:
            schema = f.read()
            cur.execute(schema)
            conn.commit()
            print('   Database schema initialized')
    else:
        print('   No schema.sql found, skipping')
    
    cur.close()
    conn.close()
except Exception as e:
    print(f'   Warning: Could not initialize schema: {e}')
" || true
fi

# Wait for RabbitMQ if RABBITMQ_HOST is set
if [ -n "$RABBITMQ_HOST" ]; then
    echo "⏳ Waiting for RabbitMQ at $RABBITMQ_HOST:${RABBITMQ_PORT:-5672}..."
    until nc -z "$RABBITMQ_HOST" "${RABBITMQ_PORT:-5672}" 2>/dev/null; do
        echo "   RabbitMQ not ready, retrying in 2s..."
        sleep 2
    done
    echo "✅ RabbitMQ is available"
fi

# Run seed script in background if SEED_ON_STARTUP is enabled
if [ "${SEED_ON_STARTUP:-true}" = "true" ] && [ -n "$ELASTICSEARCH_HOST" ]; then
    echo "🌱 Will seed index with popular sites after startup..."
    (
        # Wait for the API to be ready
        sleep 10
        python scripts/seed_index.py
    ) &
fi

echo "🎯 All dependencies ready, starting application..."
exec "$@"
