"""
Test suite for Mini Search Engine Backend

Run with: pytest tests/ -v
"""

import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSharedConfig:
    """Test shared configuration module"""
    
    def test_settings_import(self):
        """Test that settings can be imported"""
        from shared.config import settings
        assert settings is not None
    
    def test_settings_defaults(self):
        """Test default settings values"""
        from shared.config import settings
        
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.redis_port == 6379
        assert settings.elasticsearch_port == 9200
        assert settings.api_port == 8000
    
    def test_postgres_url_property(self):
        """Test PostgreSQL URL construction"""
        from shared.config import settings
        
        url = settings.postgres_url
        assert "postgresql://" in url
        assert settings.postgres_host in url
    
    def test_redis_url_property(self):
        """Test Redis URL construction"""
        from shared.config import settings
        
        url = settings.redis_url
        assert "redis://" in url
    
    def test_elasticsearch_url_property(self):
        """Test Elasticsearch URL construction"""
        from shared.config import settings
        
        url = settings.elasticsearch_url
        assert "http://" in url
        assert "9200" in url


class TestSharedUtils:
    """Test shared utility functions"""
    
    def test_url_to_hash(self):
        """Test URL hashing function"""
        from shared.utils import url_to_hash
        
        url = "https://example.com"
        hash1 = url_to_hash(url)
        hash2 = url_to_hash(url)
        
        assert hash1 == hash2  # Same URL should produce same hash
        assert len(hash1) == 64  # SHA256 produces 64 char hex string
    
    def test_md5_hash(self):
        """Test MD5 hashing function"""
        from shared.utils import md5_hash
        
        text = "test string"
        hash_value = md5_hash(text)
        
        assert len(hash_value) == 32  # MD5 produces 32 char hex string
    
    def test_tokenize(self):
        """Test text tokenization"""
        from shared.utils import tokenize
        
        text = "Hello World! This is a TEST."
        tokens = tokenize(text)
        
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        assert all(t.islower() for t in tokens)
    
    def test_get_domain(self):
        """Test domain extraction"""
        from shared.utils import get_domain
        
        assert get_domain("https://www.example.com/page") == "www.example.com"
        assert get_domain("http://test.org:8080/path") == "test.org:8080"
    
    def test_is_valid_url(self):
        """Test URL validation"""
        from shared.utils import is_valid_url
        
        assert is_valid_url("https://example.com") == True
        assert is_valid_url("http://test.org/path") == True
        assert is_valid_url("ftp://files.com") == False
        assert is_valid_url("not-a-url") == False
        assert is_valid_url("") == False
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        from shared.utils import format_timestamp
        from datetime import datetime
        
        ts = format_timestamp()
        assert "T" in ts  # ISO format has T separator
        assert ts.endswith("Z")  # Should end with Z for UTC
    
    def test_truncate_text(self):
        """Test text truncation"""
        from shared.utils import truncate_text
        
        short_text = "Hello"
        long_text = "A" * 300
        
        assert truncate_text(short_text, 200) == short_text
        assert len(truncate_text(long_text, 200)) == 200
        assert truncate_text(long_text, 200).endswith("...")
    
    def test_sanitize_query(self):
        """Test query sanitization"""
        from shared.utils import sanitize_query
        
        query = "test (query) with [special] chars"
        sanitized = sanitize_query(query)
        
        assert "\\(" in sanitized
        assert "\\[" in sanitized


class TestSharedModels:
    """Test Pydantic models"""
    
    def test_search_result_model(self):
        """Test SearchResult model"""
        from shared.models import SearchResult
        
        result = SearchResult(
            url="https://example.com",
            title="Test Page",
            description="A test page",
            score=1.5
        )
        
        assert result.url == "https://example.com"
        assert result.score == 1.5
    
    def test_crawl_request_model(self):
        """Test CrawlRequest model"""
        from shared.models import CrawlRequest
        
        request = CrawlRequest(seed_urls=["https://example.com"])
        assert len(request.seed_urls) == 1
    
    def test_page_metadata_model(self):
        """Test PageMetadata model"""
        from shared.models import PageMetadata
        from datetime import datetime
        
        page = PageMetadata(
            id="abc123",
            url="https://example.com",
            title="Test",
            crawled_at=datetime.now()
        )
        
        assert page.status == "indexed"  # Default value


class TestCrawlerComponents:
    """Test crawler service components"""
    
    def test_crawled_page_dataclass(self):
        """Test CrawledPage data structure"""
        from crawler_service.crawler import CrawledPage
        
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            description="Test page",
            content="Hello world",
            links=["https://example.com/link1"],
            crawled_at="2024-01-01T00:00:00Z",
            worker_id="test-worker",
            http_status=200,
            content_length=100,
            domain="example.com"
        )
        
        assert page.url == "https://example.com"
        
        # Test to_dict
        d = page.to_dict()
        assert d["title"] == "Test"
        
        # Test to_json
        import json
        j = page.to_json()
        parsed = json.loads(j)
        assert parsed["url"] == "https://example.com"
    
    def test_web_crawler_url_normalization(self):
        """Test URL normalization in crawler"""
        from crawler_service.crawler import WebCrawler
        
        # Create crawler (won't connect to Redis in this test)
        # We'll test the normalization logic directly
        crawler = WebCrawler.__new__(WebCrawler)
        crawler.skip_extensions = {'.jpg', '.pdf', '.zip'}
        
        # Test _normalize_url method
        url1 = "https://EXAMPLE.COM/Path/"
        normalized = crawler._normalize_url(url1)
        assert "example.com" in normalized
        assert normalized.endswith("/Path") or normalized.endswith("/path")
    
    def test_web_crawler_should_skip(self):
        """Test URL skip logic"""
        from crawler_service.crawler import WebCrawler
        
        crawler = WebCrawler.__new__(WebCrawler)
        crawler.skip_extensions = {'.jpg', '.pdf', '.zip', '.png'}
        
        assert crawler._should_skip_url("https://example.com/image.jpg") == True
        assert crawler._should_skip_url("https://example.com/doc.pdf") == True
        assert crawler._should_skip_url("ftp://files.com/file") == True
        assert crawler._should_skip_url("https://example.com/page") == False


class TestIndexerComponents:
    """Test indexer service components"""
    
    def test_text_preprocessor_tokenize(self):
        """Test text tokenization"""
        from indexer_service.indexer import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        tokens = preprocessor.tokenize("Hello World! Testing 123")
        
        assert "hello" in tokens
        assert "world" in tokens
    
    def test_text_preprocessor_stopwords(self):
        """Test stopword removal"""
        from indexer_service.indexer import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        tokens = ["the", "quick", "brown", "fox", "is", "a", "test"]
        filtered = preprocessor.remove_stopwords(tokens)
        
        assert "the" not in filtered
        assert "is" not in filtered
        assert "quick" in filtered
    
    def test_text_preprocessor_word_count(self):
        """Test word counting"""
        from indexer_service.indexer import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        count = preprocessor.get_word_count("The quick brown fox jumps over the lazy dog")
        
        # Should count meaningful words, not stopwords
        assert count > 0
        assert count < 9  # Less than total words due to stopword removal
    
    def test_index_document_dataclass(self):
        """Test IndexDocument creation"""
        from indexer_service.indexer import IndexDocument
        
        doc = IndexDocument(
            id="test123",
            url="https://example.com",
            title="Test Page",
            description="A test",
            content="Hello world content",
            domain="example.com",
            crawled_at="2024-01-01T00:00:00Z",
            indexed_at="2024-01-01T00:00:01Z",
            word_count=3
        )
        
        assert doc.id == "test123"
        
        # Test to_es_doc
        es_doc = doc.to_es_doc()
        assert "url" in es_doc
        assert "content" in es_doc
        assert es_doc["word_count"] == 3


class TestPageRankComponents:
    """Test PageRank service components"""
    
    def test_pagerank_computer_init(self):
        """Test PageRankComputer can be instantiated"""
        # Note: This will fail if Redis isn't available
        # We test the class structure only
        from ranking_service.pagerank import PageRankComputer
        
        # Check class exists and has required methods
        assert hasattr(PageRankComputer, 'compute')
        assert hasattr(PageRankComputer, 'store_scores')
        assert hasattr(PageRankComputer, 'get_top_pages')


class TestSearchAPI:
    """Test FastAPI search endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        
        # Import app but don't start it (avoid DB connections)
        # We'll mock the dependencies
        try:
            from search_api.main import app
            return TestClient(app, raise_server_exceptions=False)
        except Exception:
            pytest.skip("Cannot create test client without services")
    
    def test_root_endpoint_structure(self):
        """Test root endpoint returns expected structure"""
        # This tests the endpoint definition, not actual response
        from search_api.main import root
        import asyncio
        
        result = asyncio.run(root())
        assert "service" in result
        assert "version" in result
        assert "endpoints" in result


# Run basic import tests to catch syntax errors
class TestImports:
    """Test that all modules can be imported without errors"""
    
    def test_import_shared_config(self):
        from shared import config
        assert config is not None
    
    def test_import_shared_database(self):
        from shared import database
        assert database is not None
    
    def test_import_shared_utils(self):
        from shared import utils
        assert utils is not None
    
    def test_import_shared_models(self):
        from shared import models
        assert models is not None
    
    def test_import_shared_message_queue(self):
        from shared import message_queue
        assert message_queue is not None
    
    def test_import_crawler_service(self):
        from crawler_service import crawler
        assert crawler is not None
    
    def test_import_indexer_service(self):
        from indexer_service import indexer
        assert indexer is not None
    
    def test_import_ranking_service(self):
        from ranking_service import pagerank
        assert pagerank is not None
    
    def test_import_search_api(self):
        from search_api import main
        assert main is not None


class TestMessageQueue:
    """Test message queue components (without actual RabbitMQ)"""
    
    def test_queue_config(self):
        """Test QueueConfig dataclass"""
        from shared.message_queue import QueueConfig, CRAWLED_PAGES_QUEUE
        
        config = QueueConfig(name=CRAWLED_PAGES_QUEUE)
        assert config.name == CRAWLED_PAGES_QUEUE
        assert config.durable == True
        assert config.max_retries == 3
    
    def test_queue_names(self):
        """Test queue name constants"""
        from shared.message_queue import (
            CRAWLED_PAGES_QUEUE,
            INDEXED_PAGES_QUEUE,
            DEAD_LETTER_QUEUE,
            SEARCH_ENGINE_EXCHANGE
        )
        
        assert CRAWLED_PAGES_QUEUE == "crawled_pages"
        assert INDEXED_PAGES_QUEUE == "indexed_pages"
        assert DEAD_LETTER_QUEUE == "dead_letter"
        assert SEARCH_ENGINE_EXCHANGE == "search_engine"


class TestTFIDF:
    """Test TF-IDF algorithm implementation"""
    
    def test_term_frequency_raw(self):
        """Test raw term frequency calculation"""
        from ranking_service.tfidf import TermFrequency
        
        tokens = ['hello', 'world', 'hello', 'test', 'hello']
        
        assert TermFrequency.raw_tf('hello', tokens) == 3
        assert TermFrequency.raw_tf('world', tokens) == 1
        assert TermFrequency.raw_tf('missing', tokens) == 0
    
    def test_term_frequency_log(self):
        """Test logarithmic term frequency"""
        from ranking_service.tfidf import TermFrequency
        import math
        
        tokens = ['hello', 'hello', 'hello']
        
        # log_tf = 1 + log10(count) for count > 0
        expected = 1 + math.log10(3)
        assert abs(TermFrequency.log_tf('hello', tokens) - expected) < 0.0001
        assert TermFrequency.log_tf('missing', tokens) == 0.0
    
    def test_term_frequency_augmented(self):
        """Test augmented term frequency"""
        from ranking_service.tfidf import TermFrequency
        
        tokens = ['hello', 'hello', 'world']
        
        # augmented_tf = 0.5 + 0.5 * (count / max_count)
        # hello: 0.5 + 0.5 * (2/2) = 1.0
        # world: 0.5 + 0.5 * (1/2) = 0.75
        assert TermFrequency.augmented_tf('hello', tokens) == 1.0
        assert TermFrequency.augmented_tf('world', tokens) == 0.75
    
    def test_idf_calculation(self):
        """Test IDF calculation"""
        from ranking_service.tfidf import InverseDocumentFrequency
        
        idf_calc = InverseDocumentFrequency()
        
        # Add documents
        idf_calc.add_document(['hello', 'world'])
        idf_calc.add_document(['hello', 'test'])
        idf_calc.add_document(['foo', 'bar'])
        
        assert idf_calc.total_docs == 3
        assert idf_calc.doc_frequencies['hello'] == 2
        assert idf_calc.doc_frequencies['world'] == 1
    
    def test_idf_smooth(self):
        """Test smoothed IDF"""
        from ranking_service.tfidf import InverseDocumentFrequency
        import math
        
        idf_calc = InverseDocumentFrequency()
        idf_calc.add_document(['hello', 'world'])
        idf_calc.add_document(['hello', 'test'])
        
        # idf_smooth = log10((N + 1) / (df + 1))
        # For 'hello' with N=2, df=2: log10(3/3) = 0
        assert idf_calc.idf_smooth('hello') == 0.0
        
        # For 'world' with N=2, df=1: log10(3/2)
        expected = math.log10(3/2)
        assert abs(idf_calc.idf_smooth('world') - expected) < 0.0001
    
    def test_tfidf_calculator(self):
        """Test full TF-IDF calculator"""
        from ranking_service.tfidf import TFIDFCalculator
        
        calc = TFIDFCalculator()
        
        calc.add_document('doc1', 'The quick brown fox')
        calc.add_document('doc2', 'The lazy brown dog')
        calc.add_document('doc3', 'Quick fox jumps')
        
        assert calc.corpus_size == 3
        assert calc.vocabulary_size > 0
        
        results = calc.score_query('quick fox')
        assert len(results) > 0
        # doc1 and doc3 should have highest scores (both have quick and fox)
    
    def test_query_processor(self):
        """Test query processor"""
        from ranking_service.tfidf import QueryProcessor
        
        processor = QueryProcessor()
        
        parsed = processor.parse_query('hello world')
        assert 'terms' in parsed
        assert len(parsed['terms']) > 0
    
    def test_text_preprocessor(self):
        """Test text preprocessor"""
        from ranking_service.tfidf import TextPreprocessor
        
        preprocessor = TextPreprocessor()
        
        tokens = preprocessor.tokenize('Hello World! This is a TEST.')
        
        # Should be lowercase
        assert all(t.islower() or t.isdigit() for t in tokens)
        # Should remove stopwords
        assert 'is' not in tokens
        assert 'a' not in tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
