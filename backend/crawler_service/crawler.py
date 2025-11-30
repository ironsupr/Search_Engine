"""
Distributed Web Crawler Service

Features:
- Async HTTP fetching with aiohttp
- URL frontier with priority queue (Redis ZSET)
- Bloom filter deduplication
- Politeness (rate limiting per domain)
- robots.txt compliance
- Link extraction and normalization
- Message queue integration for indexing
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import hashlib
import json
import time
import re
from typing import Optional, List, Dict, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.database import redis_manager, db_manager
from shared.utils import url_to_hash, get_domain, is_valid_url, format_timestamp
from shared.message_queue import MessageProducer, CRAWLED_PAGES_QUEUE

# Constants
USER_AGENT = "MiniSearchBot/1.0 (+https://github.com/your-repo)"
CRAWL_TIMEOUT = 10  # seconds
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max page size
BLOOM_FILTER_SIZE = 10_000_000  # 10 million bits
BLOOM_HASH_COUNT = 7


@dataclass
class CrawledPage:
    """Data structure for a crawled page"""
    url: str
    title: str
    description: str
    content: str
    links: List[str]
    crawled_at: str
    worker_id: str
    http_status: int
    content_length: int
    domain: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class BloomFilter:
    """
    Bloom filter for URL deduplication using Redis bitmap
    
    Why Bloom filter?
    - Memory efficient: 10M URLs in ~1.2MB
    - O(1) lookup and insert
    - False positives OK (we skip some URLs), no false negatives
    """
    
    def __init__(self, redis_client, key_prefix: str = "bloom"):
        self.redis = redis_client
        self.key = f"{key_prefix}:crawled_urls"
        self.size = BLOOM_FILTER_SIZE
        self.hash_count = BLOOM_HASH_COUNT
    
    def _get_hash_positions(self, url: str) -> List[int]:
        """Generate multiple hash positions for URL"""
        positions = []
        for i in range(self.hash_count):
            # Use different salts for each hash
            hash_input = f"{url}:{i}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            positions.append(hash_value % self.size)
        return positions
    
    def add(self, url: str):
        """Add URL to bloom filter"""
        positions = self._get_hash_positions(url)
        pipe = self.redis.pipeline()
        for pos in positions:
            pipe.setbit(self.key, pos, 1)
        pipe.execute()
    
    def contains(self, url: str) -> bool:
        """Check if URL might be in bloom filter"""
        positions = self._get_hash_positions(url)
        pipe = self.redis.pipeline()
        for pos in positions:
            pipe.getbit(self.key, pos)
        results = pipe.execute()
        return all(results)  # All bits must be set
    
    def clear(self):
        """Clear the bloom filter"""
        self.redis.delete(self.key)


class URLFrontier:
    """
    URL Frontier using Redis Sorted Set
    
    Priority-based URL queue:
    - Lower score = higher priority
    - Score based on: depth, domain authority, freshness
    """
    
    def __init__(self, redis_client, key: str = "crawler:frontier"):
        self.redis = redis_client
        self.key = key
    
    def add(self, url: str, priority: float = 1.0):
        """Add URL to frontier with priority"""
        self.redis.zadd(self.key, {url: priority})
    
    def add_many(self, urls: List[tuple]):
        """Add multiple URLs: [(url, priority), ...]"""
        if urls:
            mapping = {url: priority for url, priority in urls}
            self.redis.zadd(self.key, mapping)
    
    def pop(self) -> Optional[str]:
        """Get and remove highest priority URL (compatible with older Redis)"""
        # Use ZRANGE + ZREM for Redis < 5.0 compatibility
        result = self.redis.zrange(self.key, 0, 0)
        if result:
            url = result[0]
            self.redis.zrem(self.key, url)
            return url
        return None
    
    def pop_batch(self, count: int = 10) -> List[str]:
        """Get and remove multiple URLs (compatible with older Redis)"""
        # Use ZRANGE + ZREM for Redis < 5.0 compatibility
        results = self.redis.zrange(self.key, 0, count - 1)
        if results:
            self.redis.zrem(self.key, *results)
        return list(results)
    
    def size(self) -> int:
        """Get queue size"""
        return self.redis.zcard(self.key)
    
    def clear(self):
        """Clear the frontier"""
        self.redis.delete(self.key)


class RobotsChecker:
    """
    robots.txt compliance checker with caching
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # Cache robots.txt for 1 hour
        self._parsers: Dict[str, RobotFileParser] = {}
    
    async def can_fetch(self, url: str, session: aiohttp.ClientSession) -> bool:
        """Check if URL can be crawled according to robots.txt"""
        domain = get_domain(url)
        cache_key = f"robots:{domain}"
        
        # Check cache
        cached = self.redis.get(cache_key)
        if cached is not None:
            return cached == "1"
        
        # Fetch and parse robots.txt
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
        
        try:
            async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    rp = RobotFileParser()
                    rp.parse(robots_content.splitlines())
                    
                    can_crawl = rp.can_fetch(USER_AGENT, url)
                    
                    # Cache result
                    self.redis.setex(cache_key, self.cache_ttl, "1" if can_crawl else "0")
                    
                    return can_crawl
                else:
                    # No robots.txt = allow all
                    self.redis.setex(cache_key, self.cache_ttl, "1")
                    return True
                    
        except Exception:
            # Error fetching = allow (be permissive)
            self.redis.setex(cache_key, self.cache_ttl, "1")
            return True


class DomainRateLimiter:
    """
    Per-domain rate limiting for politeness
    """
    
    def __init__(self, redis_client, delay: float = 1.0):
        self.redis = redis_client
        self.delay = delay  # Minimum seconds between requests to same domain
    
    async def wait_if_needed(self, domain: str):
        """Wait if we've recently crawled this domain"""
        key = f"ratelimit:{domain}"
        
        last_crawl = self.redis.get(key)
        if last_crawl:
            elapsed = time.time() - float(last_crawl)
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
        
        # Update last crawl time
        self.redis.setex(key, int(self.delay * 2), str(time.time()))


class WebCrawler:
    """
    Main crawler class that orchestrates crawling
    """
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.redis = redis_manager.connect()
        
        # Initialize components
        self.bloom_filter = BloomFilter(self.redis)
        self.frontier = URLFrontier(self.redis)
        self.robots_checker = RobotsChecker(self.redis)
        self.rate_limiter = DomainRateLimiter(self.redis, settings.crawler_politeness_delay)
        
        # Stats
        self.pages_crawled = 0
        self.errors = 0
        self.start_time = None
        
        # File extensions to skip
        self.skip_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.css', '.js', '.json', '.xml',
            '.exe', '.dmg', '.apk'
        }
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped"""
        parsed = urlparse(url)
        
        # Skip non-HTTP(S)
        if parsed.scheme not in ('http', 'https'):
            return True
        
        # Skip file extensions
        path_lower = parsed.path.lower()
        for ext in self.skip_extensions:
            if path_lower.endswith(ext):
                return True
        
        # Skip fragments
        if parsed.fragment:
            return True
        
        return False
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistency"""
        parsed = urlparse(url)
        
        # Remove default ports
        netloc = parsed.netloc
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        if ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        # Remove trailing slash from path (except root)
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        # Reconstruct URL without fragment
        return urlunparse((
            parsed.scheme,
            netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            ''  # No fragment
        ))
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Normalize
            normalized = self._normalize_url(absolute_url)
            
            # Skip if not valid or should be skipped
            if is_valid_url(normalized) and not self._should_skip_url(normalized):
                links.append(normalized)
        
        return list(set(links))  # Remove duplicates
    
    def _extract_content(self, html: str) -> tuple:
        """Extract title, description, and text content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Extract meta description
        description = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()
        
        # Extract body text
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
        else:
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
        
        return title, description, text[:50000]  # Limit content size
    
    async def _fetch_page(self, url: str, session: aiohttp.ClientSession) -> Optional[CrawledPage]:
        """Fetch a single page"""
        domain = get_domain(url)
        
        try:
            # Respect rate limiting
            await self.rate_limiter.wait_if_needed(domain)
            
            # Check robots.txt
            if not await self.robots_checker.can_fetch(url, session):
                print(f"⛔ Blocked by robots.txt: {url}")
                return None
            
            # Fetch page
            headers = {
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=CRAWL_TIMEOUT),
                allow_redirects=True,
                max_redirects=5
            ) as response:
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type.lower():
                    return None
                
                # Check content length
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length > MAX_CONTENT_LENGTH:
                    return None
                
                # Read content
                html = await response.text(errors='ignore')
                
                # Extract content
                title, description, text = self._extract_content(html)
                links = self._extract_links(html, str(response.url))
                
                return CrawledPage(
                    url=str(response.url),  # Use final URL after redirects
                    title=title,
                    description=description,
                    content=text,
                    links=links,
                    crawled_at=format_timestamp(),
                    worker_id=self.worker_id,
                    http_status=response.status,
                    content_length=len(html),
                    domain=domain
                )
                
        except asyncio.TimeoutError:
            print(f"⏱️ Timeout: {url}")
            self.errors += 1
            return None
        except aiohttp.ClientError as e:
            print(f"❌ Client error for {url}: {e}")
            self.errors += 1
            return None
        except Exception as e:
            print(f"❌ Error crawling {url}: {e}")
            self.errors += 1
            return None
    
    def _calculate_priority(self, url: str, depth: int) -> float:
        """
        Calculate URL priority (lower = higher priority)
        
        Factors:
        - Depth (prefer shallow pages)
        - Domain (prefer popular domains)
        - Path length (prefer shorter paths)
        """
        priority = depth * 10.0  # Base priority from depth
        
        parsed = urlparse(url)
        
        # Prefer shorter paths
        priority += len(parsed.path.split('/')) * 0.5
        
        # Prefer root pages
        if parsed.path in ('', '/'):
            priority -= 5.0
        
        # Prefer HTTPS
        if parsed.scheme == 'https':
            priority -= 1.0
        
        return max(0.0, priority)
    
    async def _publish_to_queue(self, page: CrawledPage):
        """Publish crawled page to Redis queue for indexing"""
        try:
            # Use Redis directly (simpler and works without RabbitMQ)
            queue_key = "queue:indexing"
            self.redis.rpush(queue_key, page.to_json())
        except Exception as e:
            print(f"⚠️ Failed to publish to queue: {e}")
    
    async def _save_links(self, page: CrawledPage):
        """Save discovered links to database for PageRank"""
        try:
            with db_manager.get_cursor() as cur:
                for target_url in page.links[:100]:  # Limit links per page
                    cur.execute("""
                        INSERT INTO links (source_url, target_url)
                        VALUES (%s, %s)
                        ON CONFLICT (source_url, target_url) DO NOTHING
                    """, (page.url, target_url))
        except Exception as e:
            print(f"⚠️ Error saving links: {e}")
    
    async def crawl_url(self, url: str, session: aiohttp.ClientSession, depth: int = 0) -> bool:
        """Crawl a single URL and process results"""
        
        # Check if already crawled
        if self.bloom_filter.contains(url):
            return False
        
        # Mark as crawled (even before fetching to prevent duplicates)
        self.bloom_filter.add(url)
        
        # Fetch page
        page = await self._fetch_page(url, session)
        
        if page is None:
            return False
        
        # Publish to indexing queue
        await self._publish_to_queue(page)
        
        # Save links for PageRank
        await self._save_links(page)
        
        # Add discovered links to frontier (if not too deep)
        if depth < settings.crawler_max_depth:
            new_urls = []
            for link in page.links:
                if not self.bloom_filter.contains(link):
                    priority = self._calculate_priority(link, depth + 1)
                    new_urls.append((link, priority))
            
            if new_urls:
                self.frontier.add_many(new_urls)
        
        self.pages_crawled += 1
        print(f"✅ [{self.worker_id}] Crawled: {url[:80]}... ({self.pages_crawled} total)")
        
        return True
    
    async def run(self, max_pages: int = None):
        """Main crawl loop"""
        self.start_time = time.time()
        print(f"🕷️ Crawler {self.worker_id} starting...")
        
        connector = aiohttp.TCPConnector(
            limit=10,  # Max concurrent connections
            limit_per_host=2,  # Max per domain
            ttl_dns_cache=300  # DNS cache
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            while True:
                # Check if we've reached max pages
                if max_pages and self.pages_crawled >= max_pages:
                    print(f"📊 Reached max pages limit: {max_pages}")
                    break
                
                # Get next URL from frontier
                url = self.frontier.pop()
                
                if url is None:
                    # No URLs in frontier, wait and retry
                    print(f"⏳ [{self.worker_id}] Frontier empty, waiting...")
                    await asyncio.sleep(5)
                    
                    # Check again
                    if self.frontier.size() == 0:
                        print(f"🏁 [{self.worker_id}] No more URLs. Stopping.")
                        break
                    continue
                
                # Crawl the URL
                await self.crawl_url(url, session)
        
        # Print stats
        elapsed = time.time() - self.start_time
        rate = self.pages_crawled / elapsed if elapsed > 0 else 0
        
        print(f"""
╔══════════════════════════════════════╗
║         Crawler Stats                ║
╠══════════════════════════════════════╣
║ Worker ID:    {self.worker_id:<20} ║
║ Pages Crawled: {self.pages_crawled:<19} ║
║ Errors:        {self.errors:<19} ║
║ Duration:      {elapsed:.1f}s{' ' * (17 - len(f'{elapsed:.1f}s'))} ║
║ Rate:          {rate:.2f} pages/sec{' ' * (9 - len(f'{rate:.2f}'))} ║
╚══════════════════════════════════════╝
        """)
    
    def seed(self, urls: List[str]):
        """Add seed URLs to start crawling"""
        for url in urls:
            normalized = self._normalize_url(url)
            if is_valid_url(normalized):
                self.frontier.add(normalized, priority=0.0)  # Highest priority
                print(f"🌱 Seeded: {normalized}")


async def main():
    """Entry point for crawler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mini Search Engine Crawler')
    parser.add_argument('--worker-id', default='crawler-1', help='Worker ID')
    parser.add_argument('--seed', nargs='+', help='Seed URLs to crawl')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to crawl')
    
    args = parser.parse_args()
    
    crawler = WebCrawler(worker_id=args.worker_id)
    
    # Add seed URLs if provided
    if args.seed:
        crawler.seed(args.seed)
    
    # Run crawler
    await crawler.run(max_pages=args.max_pages)


if __name__ == "__main__":
    asyncio.run(main())
