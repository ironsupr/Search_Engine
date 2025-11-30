"""
Mini Search Engine - FastAPI Search Service
"""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from elasticsearch import Elasticsearch
from contextlib import asynccontextmanager
import redis
import json
from typing import List, Dict, Optional
import hashlib
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.database import redis_manager, es_manager, db_manager

# Global clients
es = None
cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    global es, cache
    
    # Startup
    print("🚀 Starting Mini Search Engine API...")
    es = es_manager.connect()
    cache = redis_manager.connect()
    
    # Create Elasticsearch index if it doesn't exist
    try:
        if not es.indices.exists(index=settings.elasticsearch_index):
            es.indices.create(
                index=settings.elasticsearch_index,
                body={
                    "settings": {
                        "number_of_shards": 3,
                        "number_of_replicas": 1,
                        "analysis": {
                            "analyzer": {
                                "custom_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": ["lowercase", "porter_stem", "stop"]
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "url": {"type": "keyword"},
                            "title": {"type": "text", "analyzer": "english", "boost": 3.0},
                            "description": {"type": "text", "analyzer": "english", "boost": 2.0},
                            "content": {"type": "text", "analyzer": "english"},
                            "domain": {"type": "keyword"},
                            "crawled_at": {"type": "date"},
                            "indexed_at": {"type": "date"}
                        }
                    }
                }
            )
            print(f"✅ Created Elasticsearch index: {settings.elasticsearch_index}")
    except Exception as e:
        print(f"⚠️ Elasticsearch index creation: {e}")
    
    print("✅ API ready to serve requests")
    
    yield  # Application runs here
    
    # Shutdown
    print("🛑 Shutting down API...")
    es_manager.close()
    redis_manager.close()
    db_manager.close()
    print("✅ Cleanup complete")


app = FastAPI(
    title="Mini Search Engine API",
    description="Distributed search engine with caching and ranking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mini Search Engine API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search?q=query&page=1&size=10",
            "crawl": "/crawl (POST)",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    page: int = Query(1, ge=1, le=100, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Results per page")
) -> Dict:
    """
    Search endpoint with caching and ranking
    
    Args:
        q: Search query string
        page: Page number (1-indexed)
        size: Number of results per page
    
    Returns:
        Search results with metadata
    """
    start_time = datetime.now()
    
    # Generate cache key
    cache_key = f"search:{hashlib.md5(f'{q}:{page}:{size}'.encode()).hexdigest()}"
    
    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result:
        result = json.loads(cached_result)
        result["cached"] = True
        result["took_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log query
        _log_query(q, result["total"], result["took_ms"], cache_hit=True)
        
        return result
    
    # Query Elasticsearch
    try:
        es_response = es.search(
            index=settings.elasticsearch_index,
            body={
                "query": {
                    "multi_match": {
                        "query": q,
                        "fields": ["title^3", "description^2", "content"],
                        "type": "best_fields",
                        "operator": "or"
                    }
                },
                "from": (page - 1) * size,
                "size": size,
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 1
                        },
                        "title": {},
                        "description": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                },
                "_source": ["url", "title", "description", "crawled_at"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    # Extract results
    hits = es_response["hits"]["hits"]
    results = []
    
    for hit in hits:
        source = hit["_source"]
        highlight = hit.get("highlight", {})
        
        result_item = {
            "url": source.get("url", ""),
            "title": highlight.get("title", [source.get("title", "")])[0],
            "description": highlight.get("description", [source.get("description", "")])[0],
            "snippet": highlight.get("content", [""])[0] if highlight.get("content") else source.get("description", "")[:200],
            "score": hit["_score"],
            "crawled_at": source.get("crawled_at")
        }
        results.append(result_item)
    
    # Apply PageRank boosting (if available)
    results = await _apply_pagerank_boost(results)
    
    # Calculate response time
    response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # Build response
    total_hits = es_response["hits"]["total"]["value"]
    total_pages = (total_hits + size - 1) // size
    
    response = {
        "query": q,
        "total": total_hits,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "results": results,
        "took_ms": response_time_ms,
        "cached": False
    }
    
    # Cache for configured TTL
    cache.setex(cache_key, settings.cache_ttl, json.dumps(response))
    
    # Log query
    _log_query(q, total_hits, response_time_ms, cache_hit=False)
    
    return response


async def _apply_pagerank_boost(results: List[Dict]) -> List[Dict]:
    """
    Boost results using precomputed PageRank scores
    Combined score = 0.7 * TF-IDF + 0.3 * PageRank
    """
    for result in results:
        # Fetch PageRank from Redis - use first 16 chars of SHA256 hash
        # This matches how pagerank.py stores the scores
        url_hash = hashlib.sha256(result["url"].encode()).hexdigest()[:16]
        pr_key = f"pagerank:{url_hash}"
        pagerank = cache.get(pr_key)
        
        if pagerank:
            try:
                pagerank = float(pagerank)
                # Combine scores (TF-IDF from ES + PageRank)
                result["score"] = 0.7 * result["score"] + 0.3 * pagerank * 100
                result["pagerank"] = pagerank
            except ValueError:
                pass
    
    # Re-sort by combined score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results


def _log_query(query: str, results_count: int, response_time_ms: int, cache_hit: bool = False):
    """Log query to PostgreSQL for analytics"""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO query_logs (query, results_count, response_time_ms, cache_hit)
                VALUES (%s, %s, %s, %s)
            """, (query, results_count, response_time_ms, cache_hit))
    except Exception as e:
        print(f"Error logging query: {e}")


@app.post("/crawl")
async def trigger_crawl(request: Request):
    """
    Manually trigger crawl for seed URLs
    
    Body: {"seed_urls": ["https://example.com"]}
    """
    try:
        body = await request.json()
        seed_urls = body.get("seed_urls", [])
        
        if not seed_urls:
            raise HTTPException(status_code=400, detail="No seed_urls provided")
        
        # Enqueue URLs to crawler frontier
        for url in seed_urls:
            cache.zadd("crawler:frontier", {url: 0.0})
        
        return {
            "message": f"Enqueued {len(seed_urls)} URLs for crawling",
            "urls": seed_urls
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check Elasticsearch
    try:
        es.ping()
        health_status["services"]["elasticsearch"] = "up"
    except Exception as e:
        health_status["services"]["elasticsearch"] = f"down: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        cache.ping()
        health_status["services"]["redis"] = "up"
    except Exception as e:
        health_status["services"]["redis"] = f"down: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check PostgreSQL
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT 1")
        health_status["services"]["postgresql"] = "up"
    except Exception as e:
        health_status["services"]["postgresql"] = f"down: {str(e)}"
        health_status["status"] = "unhealthy"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/stats")
async def stats():
    """Get search engine statistics"""
    try:
        # Get index stats from Elasticsearch
        index_stats = es.indices.stats(index=settings.elasticsearch_index)
        doc_count = index_stats["_all"]["total"]["docs"]["count"]
        index_size = index_stats["_all"]["total"]["store"]["size_in_bytes"]
        
        # Get crawler stats from Redis
        frontier_size = cache.zcard("crawler:frontier")
        crawled_count = cache.get("stats:pages_crawled") or 0
        
        # Get query stats from PostgreSQL
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) FILTER (WHERE cache_hit = true)::float / COUNT(*) * 100 as cache_hit_rate
                FROM query_logs
                WHERE queried_at > NOW() - INTERVAL '24 hours'
            """)
            query_stats = cur.fetchone()
        
        return {
            "indexed_pages": doc_count,
            "index_size_mb": index_size / (1024 * 1024),
            "crawler_queue_size": frontier_size,
            "pages_crawled": crawled_count,
            "queries_24h": query_stats["total_queries"] if query_stats else 0,
            "avg_response_time_ms": float(query_stats["avg_response_time"]) if query_stats and query_stats["avg_response_time"] else 0,
            "cache_hit_rate": float(query_stats["cache_hit_rate"]) if query_stats and query_stats["cache_hit_rate"] else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
