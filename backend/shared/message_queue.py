"""
RabbitMQ Message Queue Integration

Provides producer/consumer classes for inter-service communication:
- Crawler → Indexer: Crawled pages queue
- Indexer → PageRank: Indexed pages notification

Why RabbitMQ?
- Decouples crawler from indexer (can scale independently)
- Reliable message delivery with acknowledgments
- Handles backpressure when indexer is slow
- Dead letter queue for failed messages
- Built-in retry mechanisms
"""

import pika
import json
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
import threading
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Queue names
CRAWLED_PAGES_QUEUE = "crawled_pages"
INDEXED_PAGES_QUEUE = "indexed_pages"
DEAD_LETTER_QUEUE = "dead_letter"

# Exchange names
SEARCH_ENGINE_EXCHANGE = "search_engine"
DEAD_LETTER_EXCHANGE = "dead_letter_exchange"


@dataclass
class QueueConfig:
    """Configuration for a queue"""
    name: str
    durable: bool = True  # Queue survives broker restart
    exclusive: bool = False  # Queue not exclusive to connection
    auto_delete: bool = False  # Queue not deleted when consumers disconnect
    
    # Dead letter configuration
    dead_letter_exchange: Optional[str] = DEAD_LETTER_EXCHANGE
    message_ttl: int = 86400000  # 24 hours in milliseconds
    max_retries: int = 3


class RabbitMQConnection:
    """
    Manages RabbitMQ connection with automatic reconnection
    
    Design decisions:
    - Uses blocking connection for simplicity
    - Automatic reconnection on failure
    - Connection pooling via singleton pattern
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._initialized = True
        
        self._max_retries = 5
        self._retry_delay = 5  # seconds
    
    def connect(self) -> pika.channel.Channel:
        """
        Establish connection to RabbitMQ
        
        Returns:
            pika.Channel: RabbitMQ channel
        """
        if self.channel and self.connection and self.connection.is_open:
            return self.channel
        
        for attempt in range(self._max_retries):
            try:
                logger.info(f"Connecting to RabbitMQ at {settings.rabbitmq_host}:{settings.rabbitmq_port}")
                
                credentials = pika.PlainCredentials(
                    settings.rabbitmq_user,
                    settings.rabbitmq_password
                )
                
                parameters = pika.ConnectionParameters(
                    host=settings.rabbitmq_host,
                    port=settings.rabbitmq_port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                    connection_attempts=3,
                    retry_delay=5
                )
                
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Enable publisher confirms for reliable delivery
                self.channel.confirm_delivery()
                
                # Set prefetch count for fair dispatch
                self.channel.basic_qos(prefetch_count=10)
                
                logger.info("✅ Connected to RabbitMQ")
                return self.channel
                
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"Connection attempt {attempt + 1}/{self._max_retries} failed: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                else:
                    raise
        
        raise Exception("Failed to connect to RabbitMQ")
    
    def close(self):
        """Close connection"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def ensure_connected(self) -> pika.channel.Channel:
        """Ensure connection is established and return channel"""
        if not self.channel or not self.connection or not self.connection.is_open:
            return self.connect()
        return self.channel


class MessageProducer:
    """
    Publishes messages to RabbitMQ queues
    
    Usage:
        producer = MessageProducer()
        producer.publish(CRAWLED_PAGES_QUEUE, {"url": "...", "content": "..."})
    """
    
    def __init__(self, exchange: str = SEARCH_ENGINE_EXCHANGE):
        self.exchange = exchange
        self._connection = RabbitMQConnection()
        self._setup_exchange()
    
    def _setup_exchange(self):
        """Set up the exchange"""
        try:
            channel = self._connection.connect()
            
            # Declare main exchange (direct type for queue routing)
            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='direct',
                durable=True
            )
            
            # Declare dead letter exchange
            channel.exchange_declare(
                exchange=DEAD_LETTER_EXCHANGE,
                exchange_type='direct',
                durable=True
            )
            
            logger.info(f"Exchange '{self.exchange}' ready")
            
        except Exception as e:
            logger.error(f"Failed to setup exchange: {e}")
            raise
    
    def declare_queue(self, config: QueueConfig):
        """Declare a queue with the given configuration"""
        channel = self._connection.ensure_connected()
        
        arguments = {}
        
        if config.dead_letter_exchange:
            arguments['x-dead-letter-exchange'] = config.dead_letter_exchange
        
        if config.message_ttl:
            arguments['x-message-ttl'] = config.message_ttl
        
        channel.queue_declare(
            queue=config.name,
            durable=config.durable,
            exclusive=config.exclusive,
            auto_delete=config.auto_delete,
            arguments=arguments if arguments else None
        )
        
        # Bind queue to exchange
        channel.queue_bind(
            exchange=self.exchange,
            queue=config.name,
            routing_key=config.name  # Use queue name as routing key
        )
        
        logger.info(f"Queue '{config.name}' declared and bound")
    
    def publish(
        self,
        queue_name: str,
        message: Dict[str, Any],
        priority: int = 0,
        expiration: Optional[str] = None
    ) -> bool:
        """
        Publish a message to a queue
        
        Args:
            queue_name: Target queue name
            message: Message data (will be JSON serialized)
            priority: Message priority (0-9)
            expiration: Message expiration in milliseconds
        
        Returns:
            bool: True if message was confirmed
        """
        try:
            channel = self._connection.ensure_connected()
            
            properties = pika.BasicProperties(
                delivery_mode=2,  # Persistent message
                content_type='application/json',
                priority=priority,
            )
            
            if expiration:
                properties.expiration = expiration
            
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=queue_name,
                body=json.dumps(message),
                properties=properties
            )
            
            logger.debug(f"Published message to {queue_name}")
            return True
            
        except pika.exceptions.UnroutableError:
            logger.error(f"Message was returned: no queue bound to {queue_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def publish_batch(
        self,
        queue_name: str,
        messages: list,
        batch_size: int = 100
    ) -> int:
        """
        Publish multiple messages efficiently
        
        Returns:
            int: Number of successfully published messages
        """
        published = 0
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            
            for message in batch:
                if self.publish(queue_name, message):
                    published += 1
        
        logger.info(f"Published {published}/{len(messages)} messages to {queue_name}")
        return published
    
    def close(self):
        """Close the producer connection"""
        self._connection.close()


class MessageConsumer:
    """
    Consumes messages from RabbitMQ queues
    
    Usage:
        def handle_message(message):
            print(f"Received: {message}")
            return True  # Return False to reject
        
        consumer = MessageConsumer()
        consumer.consume(CRAWLED_PAGES_QUEUE, handle_message)
    """
    
    def __init__(self, exchange: str = SEARCH_ENGINE_EXCHANGE):
        self.exchange = exchange
        self._connection = RabbitMQConnection()
        self._consuming = False
    
    def consume(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], bool],
        auto_ack: bool = False
    ):
        """
        Start consuming messages from a queue
        
        Args:
            queue_name: Queue to consume from
            callback: Function to process messages
                      Should return True to ack, False to reject
            auto_ack: If True, messages are automatically acknowledged
        """
        channel = self._connection.connect()
        
        # Declare queue with same settings as producer
        config = QueueConfig(name=queue_name)
        
        arguments = {}
        if config.dead_letter_exchange:
            arguments['x-dead-letter-exchange'] = config.dead_letter_exchange
        if config.message_ttl:
            arguments['x-message-ttl'] = config.message_ttl
        
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments=arguments if arguments else None
        )
        
        channel.queue_bind(
            exchange=self.exchange,
            queue=queue_name,
            routing_key=queue_name
        )
        
        def on_message(ch, method, properties, body):
            """Handle incoming message"""
            try:
                message = json.loads(body.decode('utf-8'))
                
                logger.debug(f"Received message from {queue_name}")
                
                # Call the handler
                success = callback(message)
                
                if not auto_ack:
                    if success:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        # Reject and requeue
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=True
                        )
                        
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=auto_ack
        )
        
        logger.info(f"🎧 Started consuming from {queue_name}")
        self._consuming = True
        
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            channel.stop_consuming()
        finally:
            self._consuming = False
    
    def consume_one(
        self,
        queue_name: str,
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Consume a single message with timeout
        
        Returns:
            Message dict or None if timeout
        """
        channel = self._connection.ensure_connected()
        
        method, properties, body = channel.basic_get(queue=queue_name, auto_ack=True)
        
        if method:
            return json.loads(body.decode('utf-8'))
        return None
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get number of messages in queue"""
        channel = self._connection.ensure_connected()
        
        result = channel.queue_declare(
            queue=queue_name,
            durable=True,
            passive=True  # Don't create, just check
        )
        
        return result.method.message_count
    
    def stop(self):
        """Stop consuming"""
        if self._consuming and self._connection.channel:
            self._connection.channel.stop_consuming()
        self._connection.close()


def setup_queues():
    """
    Set up all required queues for the search engine
    
    Called once at startup to ensure queues exist
    """
    producer = MessageProducer()
    
    # Crawled pages queue (crawler → indexer)
    producer.declare_queue(QueueConfig(
        name=CRAWLED_PAGES_QUEUE,
        durable=True,
        message_ttl=86400000,  # 24 hours
        max_retries=3
    ))
    
    # Indexed pages queue (indexer → pagerank)
    producer.declare_queue(QueueConfig(
        name=INDEXED_PAGES_QUEUE,
        durable=True,
        message_ttl=86400000
    ))
    
    # Dead letter queue
    producer.declare_queue(QueueConfig(
        name=DEAD_LETTER_QUEUE,
        durable=True,
        dead_letter_exchange=None  # No DLX for DLQ itself
    ))
    
    logger.info("✅ All queues set up")


# Convenience functions for common operations
def publish_crawled_page(page_data: Dict[str, Any]) -> bool:
    """Publish a crawled page to the indexing queue"""
    producer = MessageProducer()
    return producer.publish(CRAWLED_PAGES_QUEUE, page_data)


def publish_indexed_page(page_data: Dict[str, Any]) -> bool:
    """Publish an indexed page notification"""
    producer = MessageProducer()
    return producer.publish(INDEXED_PAGES_QUEUE, page_data)


if __name__ == "__main__":
    # Test the message queue
    print("Testing RabbitMQ integration...")
    
    # Set up queues
    setup_queues()
    
    # Test producer
    producer = MessageProducer()
    
    test_message = {
        "url": "https://example.com",
        "title": "Test Page",
        "content": "This is a test"
    }
    
    success = producer.publish(CRAWLED_PAGES_QUEUE, test_message)
    print(f"Published test message: {success}")
    
    # Test consumer
    consumer = MessageConsumer()
    message = consumer.consume_one(CRAWLED_PAGES_QUEUE)
    print(f"Received message: {message}")
    
    print("✅ RabbitMQ integration test complete")
