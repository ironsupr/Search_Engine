-- Mini Search Engine Database Schema

-- Pages table: metadata about crawled pages
CREATE TABLE IF NOT EXISTS pages (
    id VARCHAR(64) PRIMARY KEY,  -- SHA256 of URL
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    crawled_at TIMESTAMP NOT NULL,
    indexed_at TIMESTAMP,
    worker_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'indexed',
    http_status INT DEFAULT 200,
    content_length INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pages_crawled_at ON pages(crawled_at DESC);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_url_hash ON pages(id);

-- Links table: link graph for PageRank
CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    discovered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_url, target_url)
);

CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_url);

-- Crawl jobs: track crawl sessions
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id SERIAL PRIMARY KEY,
    seed_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    pages_crawled INT DEFAULT 0,
    pages_indexed INT DEFAULT 0,
    errors_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_created ON crawl_jobs(created_at DESC);

-- Query logs: analytics and monitoring
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    user_ip VARCHAR(45),
    results_count INT,
    response_time_ms INT,
    cache_hit BOOLEAN DEFAULT FALSE,
    queried_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_logs_queried_at ON query_logs(queried_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_query ON query_logs(query);

-- PageRank scores: precomputed ranking
CREATE TABLE IF NOT EXISTS pagerank_scores (
    url_hash VARCHAR(64) PRIMARY KEY,
    url TEXT NOT NULL,
    score FLOAT NOT NULL,
    computed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagerank_score ON pagerank_scores(score DESC);

-- Crawler queue: URLs to crawl (backup to Redis)
CREATE TABLE IF NOT EXISTS crawler_queue (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    priority FLOAT DEFAULT 1.0,
    depth INT DEFAULT 0,
    added_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_crawler_queue_priority ON crawler_queue(priority, added_at);
CREATE INDEX IF NOT EXISTS idx_crawler_queue_status ON crawler_queue(status);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for pages table
CREATE TRIGGER update_pages_updated_at BEFORE UPDATE ON pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
