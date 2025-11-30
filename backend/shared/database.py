"""
Database connection managers
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from elasticsearch import Elasticsearch
from contextlib import contextmanager
from .config import settings


class DatabaseManager:
    """PostgreSQL connection manager"""
    
    _instance = None
    _conn = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                settings.postgres_url,
                cursor_factory=RealDictCursor
            )
        return self._conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def close(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()


class RedisManager:
    """Redis connection manager"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish Redis connection"""
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                decode_responses=True
            )
        return self._client
    
    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()


class ElasticsearchManager:
    """Elasticsearch connection manager"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ElasticsearchManager, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish Elasticsearch connection"""
        if self._client is None:
            self._client = Elasticsearch(
                [settings.elasticsearch_url],
                verify_certs=settings.elasticsearch_verify_certs,
                ssl_show_warn=False
            )
        return self._client
    
    def close(self):
        """Close Elasticsearch connection"""
        if self._client:
            self._client.close()


# Global instances
db_manager = DatabaseManager()
redis_manager = RedisManager()
es_manager = ElasticsearchManager()
