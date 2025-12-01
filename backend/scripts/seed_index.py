#!/usr/bin/env python3
"""
Seed script to crawl and index popular sites on startup.
This runs after the backend starts to populate the search index.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import sys
import os
import time
import json
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.seed_urls import SEED_URLS


async def fetch_and_index_url(session, es, url: str) -> dict:
    """Fetch a URL and index it to Elasticsearch"""
    result = {"url": url, "success": False, "title": None, "error": None}
    
    try:
        headers = {
            "User-Agent": "EchoSearch/1.0 (Search Engine Crawler)"
        }
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), 
                               headers=headers, ssl=False) as response:
            if response.status != 200:
                result["error"] = f"HTTP {response.status}"
                return result
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
            result["title"] = title
            
            # Extract description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '')[:500] if meta_desc else ''
            
            # Extract text content
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            text_content = ' '.join(soup.get_text().split())[:5000]
            
            # Create document
            import hashlib
            doc_id = hashlib.sha256(url.encode()).hexdigest()
            
            doc = {
                "url": url,
                "title": title,
                "description": description,
                "content": text_content,
                "domain": urlparse(url).netloc,
                "crawled_at": datetime.utcnow().isoformat() + "Z",
                "indexed_at": datetime.utcnow().isoformat() + "Z",
            }
            
            # Index to Elasticsearch
            es.index(index=settings.elasticsearch_index, id=doc_id, document=doc)
            result["success"] = True
            
    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)[:100]
    
    return result


async def seed_index():
    """Main function to seed the search index"""
    from elasticsearch import Elasticsearch
    
    print("=" * 60)
    print("🌱 SEEDING SEARCH INDEX WITH POPULAR SITES")
    print("=" * 60)
    
    # Connect to Elasticsearch
    scheme = "https" if settings.elasticsearch_use_ssl else "http"
    es_url = f"{scheme}://{settings.elasticsearch_host}:{settings.elasticsearch_port}"
    
    print(f"📡 Connecting to Elasticsearch at {es_url}...")
    
    es = Elasticsearch(
        [es_url],
        basic_auth=(settings.elasticsearch_user, settings.elasticsearch_password),
        verify_certs=False,
        ssl_show_warn=False
    )
    
    # Wait for ES to be ready
    for i in range(30):
        try:
            if es.ping():
                print("✅ Elasticsearch connected")
                break
        except:
            print(f"   Waiting for Elasticsearch... ({i+1}/30)")
            await asyncio.sleep(2)
    else:
        print("❌ Could not connect to Elasticsearch")
        return
    
    # Check if index already has documents
    try:
        count = es.count(index=settings.elasticsearch_index)
        if count['count'] > 5:
            print(f"📚 Index already has {count['count']} documents, skipping seed")
            return
    except:
        pass  # Index might not exist yet
    
    # Create index if needed
    if not es.indices.exists(index=settings.elasticsearch_index):
        print(f"📝 Creating index: {settings.elasticsearch_index}")
        es.indices.create(
            index=settings.elasticsearch_index,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "content_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "porter_stem"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "url": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "content_analyzer",
                            "fields": {"raw": {"type": "keyword"}}
                        },
                        "description": {"type": "text", "analyzer": "content_analyzer"},
                        "content": {"type": "text", "analyzer": "content_analyzer"},
                        "domain": {"type": "keyword"},
                        "crawled_at": {"type": "date"},
                        "indexed_at": {"type": "date"}
                    }
                }
            }
        )
    
    # Crawl and index URLs
    print(f"\n🕷️  Crawling {len(SEED_URLS)} popular sites...")
    print("-" * 60)
    
    start_time = time.time()
    success_count = 0
    
    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Process in batches of 5
        for i in range(0, len(SEED_URLS), 5):
            batch = SEED_URLS[i:i+5]
            tasks = [fetch_and_index_url(session, es, url) for url in batch]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result["success"]:
                    print(f"  ✅ {result['title'][:50]}")
                    success_count += 1
                else:
                    print(f"  ❌ {result['url'][:40]}... ({result['error']})")
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    print("-" * 60)
    print(f"\n📊 SEED COMPLETE")
    print(f"   ✅ Indexed: {success_count}/{len(SEED_URLS)} sites")
    print(f"   ⏱️  Time: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_index())
