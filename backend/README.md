# Mini Search Engine - Backend

A distributed search engine built with FastAPI, featuring web crawling, indexing, ranking, and caching.

## Architecture

```
┌─────────┐    ┌───────┐    ┌─────────┐    ┌──────────────┐
│ Crawler │───▶│ Queue │───▶│ Indexer │───▶│Elasticsearch │
└─────────┘    └───────┘    └─────────┘    └──────────────┘
                                                    │
┌──────┐    ┌──────────┐    ┌───────┐             │
│ User │───▶│Search API│───▶│ Redis │◀────────────┘
└──────┘    └──────────┘    └───────┘
                  │
                  ▼
            ┌──────────┐
            │PostgreSQL│
            └──────────┘
```

## Services

- **Search API**: FastAPI service for search queries
- **Crawler Service**: Distributed web crawler with politeness
- **Indexer Service**: Processes crawled pages into Elasticsearch
- **Ranking Service**: Computes PageRank scores

## Tech Stack

- **FastAPI**: REST API framework
- **PostgreSQL**: Metadata storage
- **Elasticsearch**: Full-text search index
- **Redis**: Caching and URL frontier
- **RabbitMQ**: Message queue
- **Docker**: Containerization

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose

### Setup

1. **Clone and navigate**:
```bash
cd backend
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Start services with Docker**:
```bash
docker-compose up -d
```

6. **Initialize database**:
```bash
# Schema is automatically loaded via docker-compose
# Or manually:
psql -h localhost -U admin -d searchdb -f schema.sql
```

7. **Create Elasticsearch index**:
```bash
python scripts/init_elasticsearch.py
```

## Development

### Run Search API locally:
```bash
cd search_api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Crawler:
```bash
cd crawler_service
python crawler.py
```

### Run Indexer:
```bash
cd indexer_service
python indexer.py
```

## API Endpoints

### Search
```bash
GET /search?q=python&page=1&size=10
```

### Trigger Crawl
```bash
POST /crawl
{
  "seed_urls": ["https://example.com"]
}
```

### Health Check
```bash
GET /health
```

### Metrics
```bash
GET /metrics
```

## Testing

```bash
pytest tests/ -v --cov
```

## Project Structure

```
backend/
├── crawler_service/       # Web crawler
├── indexer_service/       # Page indexer
├── search_api/            # FastAPI search service
├── ranking_service/       # PageRank computation
├── shared/                # Shared utilities
│   ├── config.py         # Configuration
│   ├── database.py       # DB managers
│   └── utils.py          # Helper functions
├── tests/                # Unit tests
├── docker-compose.yml    # Local development
├── requirements.txt      # Python dependencies
└── schema.sql           # PostgreSQL schema
```

## Configuration

All services use environment variables from `.env`:

- **Database**: PostgreSQL connection
- **Cache**: Redis configuration
- **Search**: Elasticsearch settings
- **Queue**: RabbitMQ connection
- **Crawler**: Politeness delay, max depth
- **Cache**: TTL, max size

## Monitoring

- **Prometheus metrics**: `/metrics` endpoint
- **RabbitMQ Dashboard**: http://localhost:15672
- **Elasticsearch**: http://localhost:9200

## Tasks Progress

- [x] B1: Project scaffolding ✅
- [x] B8: Database setup ✅
- [ ] B2: Crawler service
- [ ] B3: Indexer service
- [ ] B4: TF-IDF ranking
- [ ] B5: PageRank service
- [ ] B6: Search API
- [ ] B7: Caching layer
- [ ] B9: Message queue
- [ ] B10: Docker setup (Partial ✅)
- [ ] B11: Testing

## Next Steps

1. Implement crawler service (B2)
2. Implement indexer service (B3)
3. Build Search API (B6)
4. Add PageRank computation (B5)
5. Implement comprehensive testing (B11)

## License

MIT
