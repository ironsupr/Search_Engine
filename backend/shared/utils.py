"""
Shared utility functions
"""

import hashlib
import re
from typing import List
from datetime import datetime


def url_to_hash(url: str) -> str:
    """Generate SHA256 hash from URL for document ID"""
    return hashlib.sha256(url.encode()).hexdigest()


def md5_hash(text: str) -> str:
    """Generate MD5 hash for cache keys"""
    return hashlib.md5(text.encode()).hexdigest()


def tokenize(text: str) -> List[str]:
    """Basic tokenization: lowercase and extract words"""
    return re.findall(r'\b[a-z]+\b', text.lower())


def get_domain(url: str) -> str:
    """Extract domain from URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc


def is_valid_url(url: str) -> bool:
    """Check if URL is valid HTTP/HTTPS"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False


def format_timestamp(dt: datetime = None) -> str:
    """Format datetime to ISO string"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_query(query: str) -> str:
    """Sanitize search query for Elasticsearch"""
    # Remove special characters that could break ES query
    special_chars = ['\\', '+', '-', '&', '|', '!', '(', ')', '{', '}', 
                     '[', ']', '^', '"', '~', '*', '?', ':', '/']
    for char in special_chars:
        query = query.replace(char, f'\\{char}')
    return query.strip()
