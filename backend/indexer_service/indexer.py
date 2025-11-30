"""
Indexer Service

Consumes crawled pages from the queue and indexes them to Elasticsearch.

Features:
- Text preprocessing (tokenization, stemming, stopword removal)
- Elasticsearch bulk indexing
- Metadata storage in PostgreSQL
- TF-IDF scoring (handled by Elasticsearch)
"""

import json
import re
import asyncio
from typing import List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.database import redis_manager, es_manager, db_manager
from shared.utils import url_to_hash, format_timestamp

# Try to import NLTK for text processing
try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    
    # Download required data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass
class IndexDocument:
    """Document to be indexed"""
    id: str
    url: str
    title: str
    description: str
    content: str
    domain: str
    crawled_at: str
    indexed_at: str
    word_count: int
    
    def to_es_doc(self) -> dict:
        """Convert to Elasticsearch document format"""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "domain": self.domain,
            "crawled_at": self.crawled_at,
            "indexed_at": self.indexed_at,
            "word_count": self.word_count
        }


class TextPreprocessor:
    """
    Text preprocessing for better search quality
    
    Pipeline:
    1. Lowercase
    2. Tokenize
    3. Remove stopwords
    4. Stem words (Porter stemmer)
    """
    
    def __init__(self):
        if NLTK_AVAILABLE:
            self.stemmer = PorterStemmer()
            self.stop_words = set(stopwords.words('english'))
        else:
            self.stemmer = None
            self.stop_words = {
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
                'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
                'that', 'the', 'to', 'was', 'were', 'will', 'with'
            }
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        if NLTK_AVAILABLE:
            try:
                return word_tokenize(text.lower())
            except Exception:
                pass
        
        # Fallback: simple regex tokenization
        return re.findall(r'\b[a-z]+\b', text.lower())
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove common stopwords"""
        return [t for t in tokens if t not in self.stop_words and len(t) > 2]
    
    def stem(self, tokens: List[str]) -> List[str]:
        """Apply stemming to tokens"""
        if self.stemmer:
            return [self.stemmer.stem(t) for t in tokens]
        return tokens
    
    def preprocess(self, text: str) -> str:
        """Full preprocessing pipeline"""
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.stem(tokens)
        return ' '.join(tokens)
    
    def get_word_count(self, text: str) -> int:
        """Count meaningful words in text"""
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        return len(tokens)


class Indexer:
    """
    Main indexer class that processes crawled pages
    """
    
    def __init__(self):
        self.redis = redis_manager.connect()
        self.es = es_manager.connect()
        self.preprocessor = TextPreprocessor()
        
        # Queue key (matching crawler output)
        self.queue_key = "queue:indexing"
        
        # Stats
        self.pages_indexed = 0
        self.errors = 0
        
        # Ensure index exists
        self._ensure_index()
    
    def _ensure_index(self):
        """Create Elasticsearch index if it doesn't exist"""
        index_name = settings.elasticsearch_index
        
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(
                index=index_name,
                body={
                    "settings": {
                        "number_of_shards": 3,
                        "number_of_replicas": 1,
                        "analysis": {
                            "analyzer": {
                                "content_analyzer": {
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
                            "title": {
                                "type": "text",
                                "analyzer": "english",
                                "fields": {
                                    "raw": {"type": "keyword"}
                                }
                            },
                            "description": {
                                "type": "text",
                                "analyzer": "english"
                            },
                            "content": {
                                "type": "text",
                                "analyzer": "content_analyzer"
                            },
                            "domain": {"type": "keyword"},
                            "crawled_at": {"type": "date"},
                            "indexed_at": {"type": "date"},
                            "word_count": {"type": "integer"}
                        }
                    }
                }
            )
            print(f"✅ Created Elasticsearch index: {index_name}")
    
    def _parse_crawled_page(self, data: str) -> Optional[dict]:
        """Parse JSON data from crawler"""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            return None
    
    def _create_document(self, page_data: dict) -> IndexDocument:
        """Create index document from crawled page data"""
        url = page_data.get('url', '')
        
        # Preprocess content for better search
        raw_content = page_data.get('content', '')
        processed_content = self.preprocessor.preprocess(raw_content)
        
        return IndexDocument(
            id=url_to_hash(url),
            url=url,
            title=page_data.get('title', '')[:500],  # Limit title length
            description=page_data.get('description', '')[:1000],
            content=processed_content[:100000],  # Limit content size
            domain=page_data.get('domain', ''),
            crawled_at=page_data.get('crawled_at', format_timestamp()),
            indexed_at=format_timestamp(),
            word_count=self.preprocessor.get_word_count(raw_content)
        )
    
    def index_document(self, doc: IndexDocument) -> bool:
        """Index a single document to Elasticsearch"""
        try:
            self.es.index(
                index=settings.elasticsearch_index,
                id=doc.id,
                document=doc.to_es_doc()
            )
            return True
        except Exception as e:
            print(f"❌ ES index error: {e}")
            return False
    
    def index_bulk(self, docs: List[IndexDocument]) -> int:
        """Bulk index documents for efficiency"""
        if not docs:
            return 0
        
        actions = []
        for doc in docs:
            actions.append({"index": {"_index": settings.elasticsearch_index, "_id": doc.id}})
            actions.append(doc.to_es_doc())
        
        try:
            response = self.es.bulk(body=actions, refresh=True)
            
            if response.get('errors'):
                # Count failures
                failed = sum(1 for item in response['items'] if 'error' in item.get('index', {}))
                return len(docs) - failed
            
            return len(docs)
            
        except Exception as e:
            print(f"❌ Bulk index error: {e}")
            return 0
    
    def save_metadata(self, doc: IndexDocument):
        """Save page metadata to PostgreSQL"""
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO pages (id, url, title, crawled_at, indexed_at, status, content_length)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        indexed_at = EXCLUDED.indexed_at,
                        status = 'indexed'
                """, (
                    doc.id,
                    doc.url,
                    doc.title[:500] if doc.title else None,
                    doc.crawled_at,
                    doc.indexed_at,
                    'indexed',
                    doc.word_count
                ))
        except Exception as e:
            print(f"⚠️ Metadata save error: {e}")
    
    def process_one(self) -> bool:
        """Process one page from the queue"""
        # Get page from queue (blocking pop with timeout)
        result = self.redis.blpop(self.queue_key, timeout=5)
        
        if result is None:
            return False
        
        _, data = result
        
        # Parse crawled page data
        page_data = self._parse_crawled_page(data)
        if page_data is None:
            self.errors += 1
            return False
        
        # Create document
        doc = self._create_document(page_data)
        
        # Index to Elasticsearch
        if self.index_document(doc):
            # Save metadata to PostgreSQL
            self.save_metadata(doc)
            
            self.pages_indexed += 1
            print(f"📄 Indexed: {doc.url[:70]}... ({self.pages_indexed} total)")
            return True
        else:
            self.errors += 1
            return False
    
    def process_batch(self, batch_size: int = 50) -> int:
        """Process a batch of pages"""
        # Get multiple items from queue
        pipe = self.redis.pipeline()
        for _ in range(batch_size):
            pipe.lpop(self.queue_key)
        results = pipe.execute()
        
        # Filter out None values
        pages_data = [r for r in results if r is not None]
        
        if not pages_data:
            return 0
        
        # Create documents
        docs = []
        for data in pages_data:
            page_data = self._parse_crawled_page(data)
            if page_data:
                docs.append(self._create_document(page_data))
        
        # Bulk index
        indexed = self.index_bulk(docs)
        
        # Save metadata
        for doc in docs:
            self.save_metadata(doc)
        
        self.pages_indexed += indexed
        print(f"📦 Bulk indexed: {indexed} pages ({self.pages_indexed} total)")
        
        return indexed
    
    def run(self, batch_mode: bool = True, batch_size: int = 50):
        """Main indexer loop"""
        print("📇 Indexer starting...")
        
        try:
            while True:
                queue_size = self.redis.llen(self.queue_key)
                
                if queue_size == 0:
                    # No items, wait
                    print("⏳ Queue empty, waiting...")
                    asyncio.run(asyncio.sleep(5))
                    continue
                
                if batch_mode and queue_size >= batch_size:
                    self.process_batch(batch_size)
                else:
                    self.process_one()
                    
        except KeyboardInterrupt:
            print("\n🛑 Indexer stopped")
            self._print_stats()
    
    def _print_stats(self):
        """Print indexer statistics"""
        print(f"""
╔══════════════════════════════════════╗
║         Indexer Stats                ║
╠══════════════════════════════════════╣
║ Pages Indexed: {self.pages_indexed:<20} ║
║ Errors:        {self.errors:<20} ║
╚══════════════════════════════════════╝
        """)


def main():
    """Entry point for indexer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mini Search Engine Indexer')
    parser.add_argument('--batch', action='store_true', help='Enable batch mode')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    
    args = parser.parse_args()
    
    indexer = Indexer()
    indexer.run(batch_mode=args.batch, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
