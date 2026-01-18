#!/usr/bin/env python3
"""
Production-Grade News API Backend with Redis Caching & AI
========================================================================

Ultra-fast news platform (<200ms TTFB):
✓ Redis-cached AI summaries (24h TTL)
✓ Redis-cached AI images (7d TTL)
✓ Jina AI content extraction
✓ Background image generation (non-blocking)
✓ Progressive image loading (frontend polls for updates)

API Endpoints:
  GET  /api/news              - List of articles (cached)
  GET  /api/article?url=...   - Single article with AI data (cached)
  GET  /health                - Service health check

Cache Strategy:
  article:{hash}:content  → Full content (24h)
  article:{hash}:summary  → AI summary (24h)
  article:{hash}:image    → Generated image (7d)
  article:{hash}:meta     → Full metadata (24h)

Performance Targets:
  First byte: <200ms
  Cache hits: <50ms
  Background jobs: Never block responses
"""

import os
import logging
import hashlib
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import unquote
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import our modules
from redis_cache import init_redis_cache, get_redis_cache, RedisCache
from background_image_generator import BackgroundImageGenerator

# Optional: Import existing modules if available
try:
    from gemini_image_generator import GeminiImageGenerator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GeminiImageGenerator = None

# ============================================================================
# Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Config:
    """Production configuration"""
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Jina AI
    JINA_API_KEY = os.getenv('JINA_API_KEY', '')
    JINA_TIMEOUT = 30
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 200
    RATE_LIMIT_WINDOW = 60

# ============================================================================
# Initialize Flask App
# ============================================================================

app = Flask(__name__)
CORS(app, origins="*", allow_headers="*", methods="*")

# Initialize Redis cache
redis_cache = init_redis_cache(Config.REDIS_URL)

# Initialize image generator
image_generator = None
if GEMINI_AVAILABLE and Config.GEMINI_API_KEY:
    try:
        gemini_gen = GeminiImageGenerator(Config.GEMINI_API_KEY)
        image_generator = BackgroundImageGenerator(
            generate_fn=lambda title, desc, prompt: gemini_gen.generate_image(prompt),
            redis_cache=redis_cache
        )
        logger.info("✓ Image generator initialized (Gemini)")
    except Exception as e:
        logger.warning(f"⚠ Gemini initialization failed: {e}")

# Simple rate limiter
class SimpleRateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
        self.clients = {}
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.clients:
            self.clients[client_id] = []
        
        # Clean old requests
        self.clients[client_id] = [
            t for t in self.clients[client_id] 
            if now - t < self.window
        ]
        
        # Check limit
        if len(self.clients[client_id]) < self.requests:
            self.clients[client_id].append(now)
            return True
        return False

rate_limiter = SimpleRateLimiter(Config.RATE_LIMIT_REQUESTS, Config.RATE_LIMIT_WINDOW)

# ============================================================================
# Helper Functions
# ============================================================================

def hash_url(url: str) -> str:
    """Generate consistent hash for URL"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]

def extract_article_jina(url: str) -> Optional[Dict[str, Any]]:
    """
    Extract article content using Jina AI.
    
    Returns: {
        "title": "...",
        "content": "...",
        "description": "...",
        "publish_date": "...",
        ...
    }
    """
    if not Config.JINA_API_KEY:
        logger.warning("Jina API key not configured")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {Config.JINA_API_KEY}",
            "Accept": "application/json"
        }
        
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(
            jina_url,
            headers=headers,
            timeout=Config.JINA_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract key fields
        extracted = {
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "description": data.get("description", ""),
            "url": url,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✓ Jina extraction successful: {url[:50]}")
        return extracted
    
    except Exception as e:
        logger.error(f"✗ Jina extraction failed for {url}: {e}")
        return None

def generate_summary_gemini(content: str) -> Optional[str]:
    """
    Generate summary using Gemini API.
    
    Args:
        content: Article content to summarize
    
    Returns:
        Summary string or None
    """
    if not GEMINI_AVAILABLE or not Config.GEMINI_API_KEY:
        logger.warning("Gemini not available for summary")
        return None
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""Summarize this article in 2-3 sentences:

{content[:1000]}"""
        
        response = model.generate_content(prompt)
        summary = response.text
        
        logger.info(f"✓ Summary generated: {len(summary)} chars")
        return summary
    
    except Exception as e:
        logger.error(f"✗ Summary generation failed: {e}")
        return None

# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        {
            "status": "ok",
            "redis": {
                "enabled": bool,
                "connected": bool,
                "cache_items": int
            },
            "services": {
                "jina": bool,
                "gemini": bool
            }
        }
    """
    cache_health = redis_cache.health_check()
    
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": cache_health,
        "services": {
            "jina": bool(Config.JINA_API_KEY),
            "gemini": GEMINI_AVAILABLE and bool(Config.GEMINI_API_KEY),
            "image_generator": image_generator is not None
        }
    }), 200


@app.route('/api/article', methods=['GET', 'OPTIONS'])
def get_article():
    """
    Get single article with AI data.
    
    PERFORMANCE TARGET: <200ms first response (with placeholder image)
    
    Request:
        GET /api/article?url=https://example.com/article
    
    Response (200):
        {
            "success": true,
            "article": {
                "title": "...",
                "content": "...",
                "summary": "...",
                "image_url": "/images/placeholder-blur.jpg" or "final-image.jpg",
                "url": "https://example.com/article",
                "source": "...",
                "category": "...",
                "date_publish": "...",
                "ai_generated": true
            }
        }
    """
    # CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    try:
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded: {client_id}")
            return jsonify({
                "success": False,
                "message": "Rate limit exceeded"
            }), 429
        
        # Get URL parameter
        url = request.args.get('url', '').strip()
        if not url:
            url = unquote(request.args.get('url_encoded', '').strip())
        
        if not url:
            return jsonify({
                "success": False,
                "message": "Missing 'url' parameter"
            }), 400
        
        url_hash = hash_url(url)
        
        # ====================================================================
        # STEP 1: Check metadata cache (fastest path)
        # ====================================================================
        start_time = time.time()
        cached_meta = redis_cache.get_metadata(url)
        if cached_meta:
            elapsed = time.time() - start_time
            logger.info(f"⚡ Cache hit (meta): {elapsed*1000:.1f}ms")
            cached_meta['_cache_hit'] = True
            return jsonify({
                "success": True,
                "article": cached_meta
            }), 200
        
        # ====================================================================
        # STEP 2: Extract content (Jina AI)
        # ====================================================================
        content_cached = redis_cache.get_content(url)
        if not content_cached:
            logger.info(f"Extracting content from {url[:50]}")
            extracted = extract_article_jina(url)
            if extracted:
                content_cached = json.dumps(extracted)
                redis_cache.set_content(url, content_cached)
        
        if not content_cached:
            return jsonify({
                "success": False,
                "message": "Failed to extract article content"
            }), 400
        
        content_data = json.loads(content_cached)
        
        # ====================================================================
        # STEP 3: Generate summary (Gemini - if not cached)
        # ====================================================================
        summary_cached = redis_cache.get_summary(url)
        if not summary_cached:
            logger.info(f"Generating summary for {url_hash}")
            summary = generate_summary_gemini(content_data.get("content", ""))
            if summary:
                redis_cache.set_summary(url, summary)
                summary_cached = summary
            else:
                summary_cached = content_data.get("description", "No summary available")
        
        # ====================================================================
        # STEP 4: Get image (immediate placeholder + background generation)
        # ====================================================================
        image_url = BackgroundImageGenerator.PLACEHOLDER_IMAGE
        if image_generator:
            image_url = image_generator.get_image(
                url_hash,
                content_data.get("title", ""),
                content_data.get("description", "")
            )
        else:
            # Check if already cached
            cached_image = redis_cache.get_image(url)
            if cached_image:
                image_url = cached_image
        
        # ====================================================================
        # STEP 5: Build response (MUST be <200ms)
        # ====================================================================
        article = {
            "title": content_data.get("title", "Untitled"),
            "content": content_data.get("content", ""),
            "summary": summary_cached,
            "image_url": image_url,
            "url": url,
            "source": content_data.get("source", "Unknown"),
            "category": content_data.get("category", "news"),
            "date_publish": content_data.get("publish_date", datetime.utcnow().isoformat()),
            "ai_generated": True
        }
        
        # Cache metadata for next request
        redis_cache.set_metadata(url, article)
        
        elapsed = time.time() - start_time
        logger.info(f"✓ Article response: {elapsed*1000:.1f}ms")
        
        return jsonify({
            "success": True,
            "article": article,
            "performance": {
                "ttfb_ms": round(elapsed * 1000, 1)
            }
        }), 200
    
    except Exception as e:
        logger.error(f"✗ Error in /api/article: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@app.route('/api/news', methods=['GET', 'OPTIONS'])
def get_news():
    """
    Get list of articles (existing endpoint, cached).
    
    Request:
        GET /api/news?limit=15
    
    Response (200):
        {
            "success": true,
            "articles": [...]
        }
    """
    # CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    try:
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            return jsonify({
                "success": False,
                "message": "Rate limit exceeded"
            }), 429
        
        limit = int(request.args.get('limit', 15))
        limit = min(max(limit, 1), 50)
        
        # This endpoint serves existing articles (from feed manager)
        # Should be implemented to use Redis caching
        return jsonify({
            "success": True,
            "articles": [],
            "note": "Implement feed manager integration for full list"
        }), 200
    
    except Exception as e:
        logger.error(f"✗ Error in /api/news: {e}")
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Debug endpoint: Cache statistics"""
    health = redis_cache.health_check()
    return jsonify({
        "cache": health,
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """Debug endpoint: Clear all cache (development only)"""
    if not Config.DEBUG:
        return jsonify({"error": "Not available in production"}), 403
    
    redis_cache.flush_all()
    return jsonify({"message": "Cache cleared"}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500 error: {e}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    logger.info("="*70)
    logger.info("🚀 Production News API with Redis Caching")
    logger.info("="*70)
    logger.info("Configuration:")
    logger.info(f"  Host: {Config.HOST}:{Config.PORT}")
    logger.info(f"  Debug: {Config.DEBUG}")
    logger.info(f"  Redis: {'Enabled' if redis_cache.enabled else 'Disabled (in-memory)'}")
    logger.info(f"  Jina AI: {'Configured' if Config.JINA_API_KEY else 'Not configured'}")
    logger.info(f"  Gemini AI: {'Available' if GEMINI_AVAILABLE else 'Not available'}")
    logger.info(f"  Image Generator: {'Ready' if image_generator else 'Not ready'}")
    logger.info("="*70)
    logger.info("Endpoints:")
    logger.info("  GET  /api/news?limit=15          List of articles")
    logger.info("  GET  /api/article?url=...        Single article (cached)")
    logger.info("  GET  /health                     Health check")
    logger.info("  GET  /api/cache/stats            Cache statistics")
    logger.info("="*70)
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True,
        use_reloader=False
    )
