"""
Shared configuration management for all services
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "searchdb"
    postgres_user: str = "admin"
    postgres_password: str = "password"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Elasticsearch
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_index: str = "web_pages"
    elasticsearch_user: Optional[str] = "elastic"
    elasticsearch_password: Optional[str] = None
    elasticsearch_use_ssl: bool = True
    elasticsearch_verify_certs: bool = False
    
    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Crawler
    crawler_workers: int = 5
    crawler_politeness_delay: float = 1.0
    crawler_max_depth: int = 3
    
    # Cache
    cache_ttl: int = 3600
    cache_max_size: int = 10000
    
    # PageRank
    pagerank_iterations: int = 20
    pagerank_damping: float = 0.85
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"
    
    @property
    def elasticsearch_url(self) -> str:
        """Construct Elasticsearch connection URL"""
        scheme = "https" if self.elasticsearch_use_ssl else "http"
        if self.elasticsearch_user and self.elasticsearch_password:
            return f"{scheme}://{self.elasticsearch_user}:{self.elasticsearch_password}@{self.elasticsearch_host}:{self.elasticsearch_port}"
        return f"{scheme}://{self.elasticsearch_host}:{self.elasticsearch_port}"
    
    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL"""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
