# 🔍 EchoSearch

<div align="center">

![EchoSearch](https://img.shields.io/badge/EchoSearch-Search%20Engine-6366f1?style=for-the-badge&logo=elasticsearch&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-005571?style=flat-square&logo=elasticsearch&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A modern, distributed search engine with web crawling, TF-IDF/PageRank ranking, and real-time indexing.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Reference](#-api-reference) • [Docker](#-docker-deployment)

</div>

---

## ✨ Features

- 🕷️ **Async Web Crawler** - High-performance crawler with robots.txt compliance, politeness delays, and depth control
- 📊 **TF-IDF + PageRank** - Hybrid ranking combining text relevance with link authority
- ⚡ **Real-time Indexing** - Instant search availability via `/crawl-index` API
- 🎨 **Modern UI** - React 19 frontend with Nebula dark theme, animations, and responsive design
- 🔄 **Message Queue** - RabbitMQ integration for scalable crawler-to-indexer pipeline
- 💾 **Redis Caching** - Sub-millisecond cached responses for popular queries
- 🔍 **Search Highlighting** - Query terms highlighted in results with `<mark>` tags
- 🐳 **Docker Ready** - Full containerized deployment with docker-compose

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (recommended) - [Download here](https://www.docker.com/products/docker-desktop/)
- ~4GB RAM available for Docker
- ~3GB disk space for Docker images

### Option 1: Docker (Recommended) 🐳

This is the easiest way to run EchoSearch. Docker automatically downloads and runs all services.

```bash
# Clone the repository
git clone https://github.com/ironsupr/Search_Engine.git
cd Search_Engine

# Copy environment file
cp .env.docker .env

# Start all services (first run downloads ~2GB of images)
docker-compose up -d --build
```

**That's it!** Docker will:
1. Download Elasticsearch, Redis, PostgreSQL, RabbitMQ
2. Build the frontend and backend containers
3. **Auto-seed** the index with 25+ popular sites (Google, GitHub, Wikipedia, etc.)

#### Access Points

| Service | URL |
|---------|-----|
| 🌐 **Frontend** | http://localhost |
| 📡 **API Docs** | http://localhost:8000/docs |
| 🐰 **RabbitMQ UI** | http://localhost:15672 (guest/guest) |

#### Docker Commands

```bash
# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and delete all data
docker-compose down -v

# Restart a service
docker-compose restart backend
```

---

### Option 2: Local Development

For development with hot-reload on backend/frontend:

```bash
# Start only infrastructure with Docker
docker-compose up -d elasticsearch redis postgres rabbitmq

# Backend setup (Terminal 1)
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python -m uvicorn search_api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend setup (Terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:5174 and start searching!

---

### Option 3: Manual Installation (No Docker)

<details>
<summary>Click to expand manual setup instructions</summary>

#### Install Dependencies

1. **Elasticsearch 8.x**
   - Download from [elastic.co](https://www.elastic.co/downloads/elasticsearch)
   - Run with security disabled or configure credentials

2. **Redis**
   - Windows: Download from [GitHub releases](https://github.com/microsoftarchive/redis/releases)
   - Linux/Mac: `sudo apt install redis-server` or `brew install redis`

3. **PostgreSQL 15+**
   - Download from [postgresql.org](https://www.postgresql.org/download/)
   - Create database: `createdb searchdb`

4. **RabbitMQ** (optional, for distributed crawling)
   - Download from [rabbitmq.com](https://www.rabbitmq.com/download.html)

#### Configure Environment

Create `backend/.env`:
```env
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=your_password
ELASTICSEARCH_USE_SSL=true

REDIS_HOST=localhost
REDIS_PORT=6379

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=searchdb

RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

#### Run Services

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn search_api.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

</details>

---

## 🌱 Auto-Seeding

On first Docker startup, EchoSearch automatically crawls and indexes **25+ popular sites**:

- 🔍 Google, Bing, DuckDuckGo
- 📰 Hacker News, BBC, TechCrunch, The Verge
- 💻 GitHub, Stack Overflow, DEV Community
- 📚 Python Docs, React, Vue, FastAPI, Node.js
- 📖 Wikipedia, Britannica

This takes ~15 seconds and gives you instant search results to demo!

To disable auto-seeding, set in `.env`:
```env
SEED_ON_STARTUP=false
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EchoSearch                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐                      ┌────────────────────┐     │
│  │    Frontend    │◄────────────────────►│    Backend API     │     │
│  │  React + Vite  │       REST API       │     FastAPI        │     │
│  │   Port: 5174   │                      │    Port: 8000      │     │
│  └────────────────┘                      └─────────┬──────────┘     │
│                                                    │                 │
│         ┌──────────────────────────────────────────┼──────────┐     │
│         │                                          │          │     │
│         ▼                    ▼                     ▼          ▼     │
│  ┌─────────────┐     ┌─────────────┐     ┌───────────┐ ┌──────────┐│
│  │   Crawler   │────►│  RabbitMQ   │────►│  Indexer  │ │PostgreSQL││
│  │             │     │   :5672     │     │           │ │  :5432   ││
│  └──────┬──────┘     └─────────────┘     └─────┬─────┘ └──────────┘│
│         │                                      │                    │
│         ▼                                      ▼                    │
│  ┌─────────────┐                        ┌─────────────┐            │
│  │    Redis    │◄──────────────────────►│Elasticsearch│            │
│  │    :6379    │        Cache           │    :9200    │            │
│  └─────────────┘                        └─────────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React 19, Vite, Tailwind CSS | Modern search UI with Nebula theme |
| **Backend API** | FastAPI, Python 3.11 | Search endpoints, crawl-index API |
| **Crawler** | aiohttp, BeautifulSoup | Async web page fetching |
| **Indexer** | NLTK, Elasticsearch | Text processing and indexing |
| **Elasticsearch** | v8.11 | Full-text search and inverted index |
| **Redis** | v7 | URL queue, caching, Bloom filter |
| **PostgreSQL** | v15 | Page metadata, link graph, PageRank |
| **RabbitMQ** | v3 | Message queue for crawler → indexer |

---

## 📡 API Reference

### Search

```http
GET /search?q={query}&page={1}&size={10}
```

**Response:**
```json
{
  "query": "python tutorial",
  "total": 142,
  "page": 1,
  "results": [
    {
      "url": "https://docs.python.org",
      "title": "Python Documentation",
      "snippet": "Learn <mark>Python</mark> programming...",
      "score": 15.234
    }
  ],
  "took_ms": 45,
  "cached": false
}
```

### Instant Crawl & Index

```http
POST /crawl-index/sync
Content-Type: application/json

{
  "urls": ["https://example.com", "https://news.ycombinator.com"]
}
```

**Response:**
```json
{
  "total": 2,
  "success": 2,
  "failed": 0,
  "took_ms": 1523,
  "results": [
    {"url": "https://example.com", "success": true, "title": "Example Domain"},
    {"url": "https://news.ycombinator.com", "success": true, "title": "Hacker News"}
  ]
}
```

### Health Check

```http
GET /health
```

### Full API Documentation

Interactive docs available at: http://localhost:8000/docs

---

## 🐳 Docker Deployment

### Start All Services

```bash
# Production build
docker-compose up -d --build

# With background workers (crawler + indexer)
docker-compose --profile workers up -d --build
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 80 | http://localhost |
| Backend API | 8000 | http://localhost:8000 |
| Elasticsearch | 9200 | http://localhost:9200 |
| RabbitMQ UI | 15672 | http://localhost:15672 |
| Redis | 6379 | - |
| PostgreSQL | 5432 | - |

### Environment Variables

```env
# .env file
ELASTIC_PASSWORD=elastic123
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=searchdb
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

---

## 🛠️ Development

### Project Structure

```
Search_Engine/
├── backend/
│   ├── crawler_service/     # Web crawler
│   ├── indexer_service/     # Document indexer
│   ├── search_api/          # FastAPI server
│   ├── ranking_service/     # PageRank computation
│   ├── shared/              # Shared config & utilities
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Route pages
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
cd backend
pytest tests/ -v
```

### Adding Seed URLs

```bash
# Using the crawler directly
cd backend
python -m crawler_service.crawler --seed https://example.com --max-pages 100

# Or via the API
curl -X POST http://localhost:8000/crawl-index/sync \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"]}'
```

### Admin Console

Secret admin page for manual URL indexing:
- URL: http://localhost:5174/console
- Password: `echosearch`

---

## 📚 Documentation

- [Setup Guide](SETUP.md) - Detailed installation instructions
- [Usage Guide](USAGE.md) - How to use each component
- [Docker Guide](DOCKER.md) - Container deployment

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [ironsupr](https://github.com/ironsupr)**

</div>
