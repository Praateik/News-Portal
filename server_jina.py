"""
Production-Grade News Aggregation Backend with Jina AI

A scalable, production-ready Flask API that:
1. Aggregates news from multiple RSS feeds and sources
2. Uses Jina AI (r.jina.ai) for content extraction
3. Caches extracted articles in Redis (with graceful fallback)
4. Serves articles in a format compatible with the existing frontend
5. Implements rate limiting, health checks, and proper error handling

Architecture:
- Flask + Flask-CORS for REST API
- Jina Reader API (https://r.jina.ai) for content extraction
- Redis for distributed caching (optional, with fallback)
- Feedparser for RSS feed parsing
- In-memory rate limiting (simple token bucket)

Usage:
    python server_jina.py

Environment Variables:
    JINA_API_KEY: Jina AI API authentication key (required)
    REDIS_URL: Redis connection URL (optional, e.g., redis://localhost:6379)
    PORT: Server port (default: 5001)
    HOST: Server host (default: 0.0.0.0)
    DEBUG: Debug mode (default: False)
"""

import os
import logging
import hashlib
import time
import json
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

# Optional Redis support
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Application configuration from environment variables."""

    # Jina AI Configuration
    JINA_API_KEY = os.getenv('JINA_API_KEY')
    JINA_API_BASE = 'https://r.jina.ai'
    JINA_TIMEOUT = 30  # seconds
    JINA_MAX_RETRIES = 2

    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'

    # Server Configuration
    PORT = int(os.getenv('PORT', 5001))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # API Configuration
    API_TIMEOUT = 30  # seconds
    DEFAULT_LIMIT = 15
    MAX_LIMIT = 50

    # Cache Configuration
    CACHE_TTL = 3600  # 1 hour
    FEED_REFRESH_INTERVAL = 1800  # 30 minutes
    MEMORY_CACHE_SIZE = 100

    # Rate Limiting
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 60  # seconds


# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Flask Application Factory
# ============================================================================

def create_app(config: type = Config) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config.from_object(config)

    # Enable CORS for localhost
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:*", "http://127.0.0.1:*", "file://*"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })

    return app


app = create_app(Config)


# ============================================================================
# Request Middleware
# ============================================================================

@app.before_request
def log_request() -> None:
    """Log incoming requests."""
    if request.endpoint:
        client_id = request.remote_addr
        logger.info(f"{request.method} {request.path} | Client: {client_id}")


# ============================================================================
# Redis Connection Manager
# ============================================================================

class RedisManager:
    """Manages optional Redis connection with fallback to in-memory cache."""

    def __init__(self, redis_url: str, enabled: bool = True):
        self.redis_url = redis_url
        self.enabled = enabled and REDIS_AVAILABLE
        self.client = None
        self.memory_cache = {}
        self.cache_timestamps = {}

        if self.enabled:
            try:
                self.client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.client.ping()
                logger.info(f"Connected to Redis: {redis_url}")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. Using in-memory cache.")
                self.enabled = False
                self.client = None

    def get(self, key: str) -> Optional[str]:
        """Get value from cache (Redis or memory)."""
        try:
            if self.enabled and self.client:
                value = self.client.get(key)
                if value:
                    logger.debug(f"Cache hit (Redis): {key}")
                    return value

            # Fall back to memory cache
            if key in self.memory_cache:
                if self._is_cache_valid(key):
                    logger.debug(f"Cache hit (Memory): {key}")
                    return self.memory_cache[key]
                else:
                    del self.memory_cache[key]
                    del self.cache_timestamps[key]
        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    def set(self, key: str, value: str, ttl: int = Config.CACHE_TTL) -> bool:
        """Set value in cache (Redis and/or memory)."""
        try:
            if self.enabled and self.client:
                self.client.setex(key, ttl, value)
                logger.debug(f"Cache set (Redis): {key} TTL={ttl}s")
                return True
            else:
                # Store in memory cache
                self.memory_cache[key] = value
                self.cache_timestamps[key] = time.time() + ttl
                logger.debug(f"Cache set (Memory): {key} TTL={ttl}s")
                return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            # Still save to memory as fallback
            self.memory_cache[key] = value
            self.cache_timestamps[key] = time.time() + ttl
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.enabled and self.client:
                self.client.delete(key)
            if key in self.memory_cache:
                del self.memory_cache[key]
                del self.cache_timestamps[key]
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    def _is_cache_valid(self, key: str) -> bool:
        """Check if memory cache entry is still valid."""
        if key in self.cache_timestamps:
            return self.cache_timestamps[key] > time.time()
        return False


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter using token bucket algorithm."""

    def __init__(self, requests_per_window: int, window_size: int):
        self.requests_per_window = requests_per_window
        self.window_size = window_size
        self.buckets = defaultdict(
            lambda: {'tokens': requests_per_window, 'last_refill': time.time()})
        self.lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request."""
        with self.lock:
            bucket = self.buckets[client_id]
            now = time.time()
            elapsed = now - bucket['last_refill']

            # Refill tokens based on elapsed time
            tokens_to_add = (elapsed / self.window_size) * \
                self.requests_per_window
            bucket['tokens'] = min(
                self.requests_per_window, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now

            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            return False


# ============================================================================
# News Source Configuration
# ============================================================================

class NewsSource:
    """Represents a news source with RSS feed or URL."""

    def __init__(self, name: str, feed_url: str, category: str = 'news'):
        self.name = name
        self.feed_url = feed_url
        self.category = category
        self.last_updated = None
        self.articles = []

    def fetch_articles(self) -> List[Dict[str, str]]:
        """Fetch articles from RSS feed."""
        try:
            logger.info(f"Fetching articles from {self.name}")
            feed = feedparser.parse(self.feed_url)

            if not feed.entries:
                logger.warning(f"No articles found in {self.name}")
                return []

            articles = []
            for entry in feed.entries[:Config.DEFAULT_LIMIT]:
                article = {
                    'title': entry.get('title', 'Untitled'),
                    'headline': entry.get('title', 'Untitled'),
                    'description': entry.get('summary', '') or entry.get('description', ''),
                    'url': entry.get('link', ''),
                    'source': self.name,
                    'category': self.category,
                    'published_time': entry.get('published', datetime.utcnow().isoformat()),
                    'image_url': self._extract_image_url(entry),
                    'content': None,  # Will be filled by Jina AI
                    'language': 'en'
                }
                if article['url']:
                    articles.append(article)

            self.articles = articles
            self.last_updated = datetime.utcnow()
            logger.info(f"Fetched {len(articles)} articles from {self.name}")
            return articles
        except Exception as e:
            logger.error(f"Error fetching from {self.name}: {e}")
            return []

    def _extract_image_url(self, entry) -> Optional[str]:
        """Extract image URL from feed entry."""
        try:
            if hasattr(entry, 'media_content') and entry.media_content:
                return entry.media_content[0].get('url')
            if hasattr(entry, 'image') and entry.image:
                return entry.image.get('href')
            if hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if 'image' in enclosure.get('type', ''):
                        return enclosure.get('href')
        except Exception:
            pass
        return None


# ============================================================================
# Jina AI Content Extractor
# ============================================================================

class JinaExtractor:
    """Handles content extraction via Jina AI Reader API."""

    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 2):
        if not api_key:
            raise ValueError("JINA_API_KEY is required")

        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def extract(self, url: str) -> Tuple[Optional[Dict], bool]:
        """
        Extract article content from URL using Jina AI.

        Returns:
            (article_dict, success)
        """
        try:
            url = self._normalize_url(url)
            if not self._is_valid_url(url):
                logger.warning(f"Invalid URL: {url}")
                return None, False

            logger.info(f"Extracting content from {url}")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": "NewsPortal/1.0"
            }

            for attempt in range(self.max_retries + 1):
                try:
                    jina_url = f"{Config.JINA_API_BASE}/{url}"
                    response = requests.get(
                        jina_url,
                        headers=headers,
                        timeout=self.timeout
                    )

                    if response.status_code == 200:
                        data = response.json()
                        extracted = {
                            'title': (data.get('title') or '').strip(),
                            'content': (data.get('content') or '').strip(),
                            'description': (data.get('description') or data.get('content', '')[:200]).strip(),
                            'language': data.get('language', 'en'),
                            'published_time': data.get('publishedTime') or data.get('published_time') or datetime.utcnow().isoformat(),
                            'url': url,
                            'image_url': data.get('image_url') or data.get('image'),
                        }
                        logger.info(f"Successfully extracted: {url}")
                        return extracted, True

                    elif response.status_code == 429:
                        logger.warning(
                            f"Rate limited by Jina API. Attempt {attempt + 1}/{self.max_retries + 1}")
                        if attempt < self.max_retries:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return None, False
                    else:
                        logger.warning(
                            f"Jina API error: {response.status_code}")
                        return None, False

                except requests.exceptions.Timeout:
                    logger.warning(
                        f"Timeout extracting {url}. Attempt {attempt + 1}/{self.max_retries + 1}")
                    if attempt < self.max_retries:
                        time.sleep(1)
                        continue
                    return None, False
                except requests.exceptions.ConnectionError as e:
                    logger.warning(
                        f"Connection error: {e}. Attempt {attempt + 1}/{self.max_retries + 1}")
                    if attempt < self.max_retries:
                        time.sleep(1)
                        continue
                    return None, False

        except Exception as e:
            logger.error(
                f"Unexpected error extracting {url}: {e}", exc_info=True)

        return None, False

    def _normalize_url(self, url: str) -> str:
        """Remove tracking parameters and normalize URL."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

            # Remove tracking parameters
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign',
                               'utm_term', 'utm_content', 'fbclid', 'gclid'}
            filtered_params = {k: v for k, v in params.items(
            ) if k.lower() not in tracking_params}

            new_query = urlencode(filtered_params, doseq=True)
            new_url = urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

            return new_url
        except Exception as e:
            logger.warning(f"Error normalizing URL: {e}")
            return url

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ('http', 'https') and parsed.netloc)
        except Exception:
            return False


# ============================================================================
# News Feed Manager
# ============================================================================

class NewsFeedManager:
    """Manages multiple news sources and aggregates articles."""

    def __init__(self, redis_manager: RedisManager, jina_extractor: JinaExtractor):
        self.redis_manager = redis_manager
        self.jina_extractor = jina_extractor
        self.sources: List[NewsSource] = []
        self.all_articles: List[Dict] = []
        self.last_feed_update = None
        self._init_sources()

    def _init_sources(self):
        """Initialize news sources."""
        # Add predefined news sources with RSS feeds
        self.sources = [
            NewsSource(
                'CNN', 'http://feeds.reuters.com/reuters/topNews', 'news'),
            NewsSource('BBC', 'http://feeds.bbci.co.uk/news/rss.xml', 'news'),
            NewsSource('The Guardian',
                       'https://www.theguardian.com/world/rss', 'news'),
            NewsSource('Setopati', 'https://ratopati.com/rss', 'news'),
            NewsSource(
                'TechCrunch', 'http://feeds.techcrunch.com/TechCrunch/', 'technology'),
            NewsSource('Hacker News',
                       'https://news.ycombinator.com/rss', 'technology'),
            NewsSource('ESPN', 'https://www.espn.com/espn/rss/news', 'sports'),
            NewsSource(
                'Entertainment', 'http://feeds.reuters.com/reuters/entertainmentNews', 'entertainment'),
        ]
        logger.info(f"Initialized {len(self.sources)} news sources")

    def refresh_feed(self, force: bool = False) -> List[Dict]:
        """
        Refresh news feed from all sources.

        Args:
            force: Force refresh even if feed was recently updated

        Returns:
            List of article dictionaries
        """
        # Check if refresh is needed
        if not force and self.last_feed_update:
            elapsed = (datetime.utcnow() -
                       self.last_feed_update).total_seconds()
            if elapsed < Config.FEED_REFRESH_INTERVAL:
                logger.debug(
                    f"Feed already fresh (updated {elapsed:.0f}s ago)")
                return self.all_articles

        logger.info("Refreshing news feed from all sources")
        self.all_articles = []

        # Fetch articles from all sources in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(
                source.fetch_articles): source for source in self.sources}

            for future in as_completed(futures):
                try:
                    articles = future.result()
                    self.all_articles.extend(articles)
                except Exception as e:
                    logger.error(f"Error fetching articles: {e}")

        self.last_feed_update = datetime.utcnow()
        logger.info(f"Feed refreshed: {len(self.all_articles)} total articles")
        return self.all_articles

    def get_articles(self, limit: int = Config.DEFAULT_LIMIT) -> List[Dict]:
        """
        Get articles and enrich them with full content via Jina AI.

        Args:
            limit: Number of articles to return

        Returns:
            List of article dictionaries with full content
        """
        limit = min(limit, Config.MAX_LIMIT)

        # Refresh feed if needed
        articles = self.refresh_feed()

        # Sort by published time (most recent first) and limit
        try:
            sorted_articles = sorted(
                articles,
                key=lambda x: x.get('published_time', ''),
                reverse=True
            )[:limit]
        except Exception as e:
            logger.warning(f"Error sorting articles: {e}")
            sorted_articles = articles[:limit]

        # Enrich articles with full content
        enriched = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(
                self._enrich_article, article): article for article in sorted_articles}

            for future in as_completed(futures):
                try:
                    enriched_article = future.result()
                    if enriched_article:
                        enriched.append(enriched_article)
                except Exception as e:
                    logger.error(f"Error enriching article: {e}")

        return enriched[:limit]

    def _enrich_article(self, article: Dict) -> Optional[Dict]:
        """
        Enrich article with full content from Jina AI or cache.

        Args:
            article: Article dictionary with at least 'url' field

        Returns:
            Enriched article dictionary or None
        """
        if not article.get('url'):
            return article

        # Generate cache key
        cache_key = f"news:article:{hashlib.sha256(article['url'].encode()).hexdigest()}"

        # Try to get from cache
        cached = self.redis_manager.get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                return {**article, **cached_data}
            except Exception as e:
                logger.warning(f"Error parsing cached article: {e}")

        # Extract content via Jina AI
        extracted, success = self.jina_extractor.extract(article['url'])

        if success and extracted:
            # Update article with extracted content
            article_data = {
                'title': extracted.get('title') or article.get('title'),
                'content': extracted.get('content'),
                'description': extracted.get('description') or article.get('description'),
                'language': extracted.get('language', 'en'),
                'published_time': extracted.get('published_time') or article.get('published_time'),
                'image_url': extracted.get('image_url') or article.get('image_url'),
            }

            # Cache the extracted data
            try:
                self.redis_manager.set(
                    cache_key,
                    json.dumps(article_data),
                    ttl=Config.CACHE_TTL
                )
            except Exception as e:
                logger.warning(f"Error caching article: {e}")

            return {**article, **article_data}

        # If extraction failed, return article without full content
        return article


# ============================================================================
# Initialize Services
# ============================================================================
# Initialize Redis manager
redis_manager = RedisManager(Config.REDIS_URL, Config.REDIS_ENABLED)

# Initialize Jina extractor
try:
    jina_extractor = JinaExtractor(
        Config.JINA_API_KEY,
        timeout=Config.JINA_TIMEOUT,
        max_retries=Config.JINA_MAX_RETRIES
    )
except ValueError as e:
    logger.error(f"Failed to initialize Jina extractor: {e}")
    jina_extractor = None

# Initialize news feed manager
feed_manager = NewsFeedManager(
    redis_manager, jina_extractor) if jina_extractor else None

# Initialize rate limiter
rate_limiter = RateLimiter(
    Config.RATE_LIMIT_REQUESTS, Config.RATE_LIMIT_WINDOW)


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check() -> Tuple[Dict, int]:
    """
    Health check endpoint.

    Returns:
        {
            "status": "ok",
            "service": "News Aggregation API",
            "redis": "connected|disconnected",
            "jina": "configured|not_configured"
        }
    """
    return jsonify({
        "status": "ok",
        "service": "News Aggregation API",
        "version": "2.0.0",
        "redis": "connected" if redis_manager.enabled else "disconnected",
        "jina": "configured" if jina_extractor else "not_configured"
    }), 200


@app.route('/api/news', methods=['GET', 'OPTIONS'])
def get_news() -> Tuple[Dict, int]:
    """
    Primary API endpoint: Get aggregated news feed.

    Frontend expects this format!

    Request:
        GET /api/news?limit=15

    Response (Success - 200):
        {
            "success": true,
            "articles": [
                {
                    "title": "Article Title",
                    "headline": "Article Headline",
                    "description": "Article summary...",
                    "content": "Full article content...",
                    "url": "https://example.com/article",
                    "image_url": "https://example.com/image.jpg",
                    "source": "Source Name",
                    "category": "technology",
                    "published_time": "2025-01-17T10:00:00Z",
                    "language": "en"
                }
            ]
        }

    Response (Error - always 200, never 400):
        {
            "success": false,
            "message": "Error description"
        }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            return jsonify({
                "success": False,
                "message": "Rate limit exceeded. Please try again later."
            }), 200  # Return 200 per requirements

        # Get limit parameter (no url parameter!)
        try:
            limit = int(request.args.get('limit', Config.DEFAULT_LIMIT))
            limit = min(limit, Config.MAX_LIMIT)
            limit = max(limit, 1)
        except (ValueError, TypeError):
            limit = Config.DEFAULT_LIMIT

        if not feed_manager:
            logger.error("Feed manager not initialized")
            return jsonify({
                "success": False,
                "message": "Service temporarily unavailable"
            }), 200

        # Get articles
        articles = feed_manager.get_articles(limit=limit)

        if not articles:
            logger.warning("No articles retrieved")
            return jsonify({
                "success": False,
                "message": "No articles available at this time"
            }), 200

        return jsonify({
            "success": True,
            "articles": articles
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in /api/news: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while fetching news"
        }), 200


@app.route('/api/extract', methods=['POST', 'OPTIONS'])
def extract_article() -> Tuple[Dict, int]:
    """
    Extract full article content from a single URL via Jina AI.

    Request:
        POST /api/extract
        Content-Type: application/json
        {
            "url": "https://example.com/article"
        }

    Response (Success - 200):
        {
            "success": true,
            "data": {
                "title": "Article Title",
                "headline": "Article Headline",
                "description": "Article summary",
                "content": "Full article content...",
                "url": "https://example.com/article",
                "image_url": "https://example.com/image.jpg",
                "source": "Source",
                "category": "news",
                "published_time": "2025-01-17T10:00:00Z",
                "language": "en"
            }
        }

    Response (Error - 200):
        {
            "success": false,
            "message": "Error description"
        }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            return jsonify({
                "success": False,
                "message": "Rate limit exceeded"
            }), 200

        # Validate request
        if not request.is_json:
            logger.warning("Invalid Content-Type for /api/extract")
            return jsonify({
                "success": False,
                "message": "Content-Type must be application/json"
            }), 200

        try:
            payload = request.get_json(silent=False) or {}
        except Exception as e:
            logger.warning(f"Invalid JSON: {e}")
            return jsonify({
                "success": False,
                "message": "Invalid JSON format"
            }), 200

        url = payload.get('url', '').strip()

        if not url:
            logger.warning("Missing URL in /api/extract")
            return jsonify({
                "success": False,
                "message": "Missing 'url' parameter"
            }), 200

        if not jina_extractor:
            logger.error("Jina extractor not initialized")
            return jsonify({
                "success": False,
                "message": "Extraction service not available"
            }), 200

        # Extract content
        extracted, success = jina_extractor.extract(url)

        if not success or not extracted:
            return jsonify({
                "success": False,
                "message": "Failed to extract article content"
            }), 200

        # Try to cache the result
        try:
            cache_key = f"news:article:{hashlib.sha256(url.encode()).hexdigest()}"
            redis_manager.set(cache_key, json.dumps(
                extracted), ttl=Config.CACHE_TTL)
        except Exception as e:
            logger.warning(f"Error caching extracted article: {e}")

        return jsonify({
            "success": True,
            "data": extracted
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in /api/extract: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred during extraction"
        }), 200


@app.route('/', methods=['GET'])
def index() -> Tuple[Dict, int]:
    """Root endpoint with API documentation."""
    return jsonify({
        "service": "News Aggregation API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "/api/news": {
                "method": "GET",
                "description": "Get aggregated news feed (frontend endpoint)",
                "parameters": {
                    "limit": "Number of articles (default: 15, max: 50)"
                },
                "example": "/api/news?limit=15"
            },
            "/api/extract": {
                "method": "POST",
                "description": "Extract full article content from URL",
                "body": {"url": "https://example.com/article"},
                "example": "POST /api/extract with JSON body"
            },
            "/health": {
                "method": "GET",
                "description": "Service health check"
            }
        }
    }), 200


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error) -> Tuple[Dict, int]:
    """Handle 404 errors."""
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({
        "success": False,
        "message": "Endpoint not found"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error) -> Tuple[Dict, int]:
    """Handle 405 errors."""
    logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
    return jsonify({
        "success": False,
        "message": "Method not allowed"
    }), 405


@app.errorhandler(500)
def internal_error(error) -> Tuple[Dict, int]:
    """Handle 500 errors."""
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
    return jsonify({
        "success": False,
        "message": "Internal server error"
    }), 500


# ============================================================================
# Application Entry Point
# ============================================================================
if __name__ == '__main__':
    # Validate configuration
    if not Config.JINA_API_KEY:
        logger.error("="*70)
        logger.error("JINA_API_KEY environment variable is not set!")
        logger.error("The /api/extract and /api/news endpoints will not work.")
        logger.error("Set it with: export JINA_API_KEY='your_api_key_here'")
        logger.error("="*70)

    # Log startup info
    logger.info("="*70)
    logger.info("Starting News Aggregation API (v2.0.0)")
    logger.info("="*70)
    logger.info("Configuration:")
    logger.info(f"  Host: {Config.HOST}")
    logger.info(f"  Port: {Config.PORT}")
    logger.info(f"  Debug: {Config.DEBUG}")
    logger.info(f"  Jina API: {Config.JINA_API_BASE}")
    logger.info(f"  Jina Timeout: {Config.JINA_TIMEOUT}s")
    logger.info(
        f"  Redis: {'Enabled' if Config.REDIS_ENABLED else 'Disabled'}")
    logger.info(f"  Cache TTL: {Config.CACHE_TTL}s")
    logger.info(
        f"  Rate Limit: {Config.RATE_LIMIT_REQUESTS} req/{Config.RATE_LIMIT_WINDOW}s")
    logger.info("="*70)
    logger.info("Available endpoints:")
    logger.info(f"  GET  /api/news?limit=15     (Frontend endpoint)")
    logger.info(f"  POST /api/extract           (Single article extraction)")
    logger.info(f"  GET  /health                (Health check)")
    logger.info(f"  GET  /                      (API documentation)")
    logger.info("="*70)
    logger.info(f"Server available at:")
    logger.info(f"  http://{Config.HOST}:{Config.PORT}/")
    logger.info(f"  http://localhost:{Config.PORT}/")
    logger.info(f"  http://127.0.0.1:{Config.PORT}/")
    logger.info("="*70)

    # Run Flask server
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False,
        threaded=True
    )
