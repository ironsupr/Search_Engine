"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime


# Request Models
class CrawlRequest(BaseModel):
    """Request to trigger crawl job"""
    seed_urls: List[str] = Field(..., min_length=1, description="URLs to start crawling from")
    max_depth: Optional[int] = Field(3, ge=1, le=10, description="Maximum crawl depth")
    
    model_config = {"json_schema_extra": {
        "example": {
            "seed_urls": ["https://example.com", "https://docs.python.org"],
            "max_depth": 3
        }
    }}


# Response Models
class SearchResult(BaseModel):
    """Single search result"""
    url: str
    title: str
    description: Optional[str] = ""
    snippet: Optional[str] = ""
    score: float
    pagerank: Optional[float] = None
    crawled_at: Optional[str] = None


class SearchResponse(BaseModel):
    """Search endpoint response"""
    query: str
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    results: List[SearchResult]
    took_ms: int
    cached: bool = False


class HealthStatus(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    services: dict


class StatsResponse(BaseModel):
    """Statistics response"""
    indexed_pages: int
    index_size_mb: float
    crawler_queue_size: int
    pages_crawled: int
    queries_24h: int
    avg_response_time_ms: float
    cache_hit_rate: float


class CrawlResponse(BaseModel):
    """Crawl trigger response"""
    message: str
    urls: List[str]
    job_id: Optional[int] = None


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Page Models (for database)
class PageMetadata(BaseModel):
    """Page metadata stored in database"""
    id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    crawled_at: datetime
    indexed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    status: str = "indexed"
    http_status: int = 200
    content_length: Optional[int] = None


class LinkRecord(BaseModel):
    """Link relationship between pages"""
    source_url: str
    target_url: str
    anchor_text: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class CrawlJob(BaseModel):
    """Crawl job tracking"""
    id: Optional[int] = None
    seed_url: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pages_crawled: int = 0
    pages_indexed: int = 0
    errors_count: int = 0
