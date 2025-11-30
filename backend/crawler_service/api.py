"""
FastAPI endpoints for crawler management

Provides API to:
- Start/stop crawlers
- Add seed URLs
- Check crawler status
- View crawl stats
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.database import redis_manager, db_manager
from crawler import WebCrawler

app = FastAPI(
    title="Crawler Management API",
    description="API to manage distributed web crawlers",
    version="1.0.0"
)

# Global crawler instance
crawler_instance: Optional[WebCrawler] = None
crawler_task: Optional[asyncio.Task] = None


class SeedRequest(BaseModel):
    urls: List[str]
    
    model_config = {"json_schema_extra": {
        "example": {
            "urls": ["https://example.com", "https://docs.python.org"]
        }
    }}


class CrawlerConfig(BaseModel):
    max_pages: Optional[int] = None
    worker_id: str = "crawler-api"
    
    model_config = {"json_schema_extra": {
        "example": {
            "max_pages": 1000,
            "worker_id": "crawler-1"
        }
    }}


@app.get("/")
async def root():
    return {
        "service": "Crawler Management API",
        "version": "1.0.0",
        "endpoints": {
            "seed": "POST /seed - Add seed URLs",
            "start": "POST /start - Start crawler",
            "stop": "POST /stop - Stop crawler",
            "status": "GET /status - Crawler status",
            "stats": "GET /stats - Crawl statistics"
        }
    }


@app.post("/seed")
async def seed_urls(request: SeedRequest):
    """Add seed URLs to the crawler frontier"""
    redis = redis_manager.connect()
    
    added = 0
    for url in request.urls:
        # Add to frontier with highest priority
        redis.zadd("crawler:frontier", {url: 0.0})
        added += 1
    
    return {
        "message": f"Added {added} seed URLs to frontier",
        "urls": request.urls,
        "frontier_size": redis.zcard("crawler:frontier")
    }


@app.post("/start")
async def start_crawler(config: CrawlerConfig):
    """Start the crawler"""
    global crawler_instance, crawler_task
    
    if crawler_task and not crawler_task.done():
        raise HTTPException(status_code=400, detail="Crawler is already running")
    
    crawler_instance = WebCrawler(worker_id=config.worker_id)
    
    # Start crawler in background
    crawler_task = asyncio.create_task(
        crawler_instance.run(max_pages=config.max_pages)
    )
    
    return {
        "message": "Crawler started",
        "worker_id": config.worker_id,
        "max_pages": config.max_pages
    }


@app.post("/stop")
async def stop_crawler():
    """Stop the crawler"""
    global crawler_task
    
    if crawler_task is None or crawler_task.done():
        raise HTTPException(status_code=400, detail="Crawler is not running")
    
    crawler_task.cancel()
    
    try:
        await crawler_task
    except asyncio.CancelledError:
        pass
    
    return {"message": "Crawler stopped"}


@app.get("/status")
async def crawler_status():
    """Get crawler status"""
    global crawler_instance, crawler_task
    
    redis = redis_manager.connect()
    
    is_running = crawler_task is not None and not crawler_task.done()
    
    status = {
        "running": is_running,
        "frontier_size": redis.zcard("crawler:frontier"),
        "queue_size": redis.llen("queue:indexing")
    }
    
    if crawler_instance and is_running:
        status.update({
            "worker_id": crawler_instance.worker_id,
            "pages_crawled": crawler_instance.pages_crawled,
            "errors": crawler_instance.errors
        })
    
    return status


@app.get("/stats")
async def crawler_stats():
    """Get detailed crawl statistics"""
    redis = redis_manager.connect()
    
    stats = {
        "frontier_size": redis.zcard("crawler:frontier"),
        "indexing_queue_size": redis.llen("queue:indexing"),
        "total_crawled": int(redis.get("stats:pages_crawled") or 0)
    }
    
    # Get database stats
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM pages")
            result = cur.fetchone()
            stats["indexed_pages"] = result["count"] if result else 0
            
            cur.execute("SELECT COUNT(*) as count FROM links")
            result = cur.fetchone()
            stats["discovered_links"] = result["count"] if result else 0
            
            cur.execute("""
                SELECT status, COUNT(*) as count 
                FROM crawl_jobs 
                GROUP BY status
            """)
            jobs = cur.fetchall()
            stats["crawl_jobs"] = {row["status"]: row["count"] for row in jobs}
            
    except Exception as e:
        stats["db_error"] = str(e)
    
    return stats


@app.delete("/frontier")
async def clear_frontier():
    """Clear the URL frontier"""
    redis = redis_manager.connect()
    redis.delete("crawler:frontier")
    return {"message": "Frontier cleared"}


@app.delete("/bloom")
async def clear_bloom_filter():
    """Clear the bloom filter (allows re-crawling)"""
    redis = redis_manager.connect()
    redis.delete("bloom:crawled_urls")
    return {"message": "Bloom filter cleared"}


@app.get("/health")
async def health():
    """Health check"""
    try:
        redis = redis_manager.connect()
        redis.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
