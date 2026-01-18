# Production-Grade News Aggregation Backend

## Overview

The refactored `server_jina.py` is a **production-ready** Flask API that aggregates news from multiple RSS feeds and uses **Jina AI** for intelligent article content extraction. It's designed to work seamlessly with your existing frontend without any modifications required.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (news-website-ui)                   │
│                   GET /api/news?limit=15                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Production Backend (server_jina.py)             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ NewsFeedManager                                          │   │
│  │  - Aggregates articles from 7 RSS feeds                 │   │
│  │  - Manages parallel article fetching                     │   │
│  │  - 30-minute feed refresh interval                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│              │                                 │                  │
│              ▼                                 ▼                  │
│  ┌──────────────────────┐        ┌──────────────────────┐       │
│  │ NewsSource Classes   │        │ JinaExtractor        │       │
│  │  - CNN               │        │  - Extracts content  │       │
│  │  - BBC               │        │  - Retry logic (2x)  │       │
│  │  - Guardian          │        │  - URL normalization │       │
│  │  - TechCrunch        │        │  - Timeout handling  │       │
│  │  - Hacker News       │        │  - Rate limiting     │       │
│  │  - ESPN              │        │                      │       │
│  │  - Entertainment     │        │  Uses: r.jina.ai     │       │
│  └──────────────────────┘        └──────────────────────┘       │
│                                            │                      │
│                                            ▼                      │
│                         ┌──────────────────────────┐             │
│                         │ RedisManager              │             │
│                         │ (with fallback cache)    │             │
│                         │  - Redis (optional)      │             │
│                         │  - In-memory fallback    │             │
│                         │  - 1-hour TTL            │             │
│                         └──────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────────┐          ┌──────────────────┐             │
│  │ Jina AI (r.jina)│          │ RSS News Feeds   │             │
│  │ Content Extract │          │ 7 trusted sources│             │
│  └──────────────────┘          └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### ✅ Frontend Compatibility
- **GET /api/news?limit=15** - Returns articles in exact format expected by frontend
- No `?url=` parameter required
- Success/failure JSON responses with consistent structure
- Always returns HTTP 200 (graceful error handling)

### ✅ News Aggregation
- **7 RSS feeds** from trusted sources:
  - Reuters (Top News, Entertainment)
  - BBC News
  - The Guardian
  - TechCrunch
  - Hacker News
  - ESPN Sports
- Configurable and easily extensible

### ✅ Jina AI Integration
- **Content extraction only** (not feed generation)
- Full article text extraction
- Metadata extraction (title, published time, language)
- Automatic URL normalization (removes tracking parameters)
- Retry logic with exponential backoff
- Timeout handling (30 seconds)
- Rate limit handling (429 responses)

### ✅ Intelligent Caching
- **Redis support** (optional, with automatic fallback)
- Cache key: `news:article:<sha256(url)>`
- 1-hour TTL per article
- Graceful degradation if Redis is unavailable
- In-memory fallback for development/testing

### ✅ Security & Performance
- **Rate limiting**: 100 requests per 60 seconds per IP
- **CORS**: Properly configured for localhost
- **Error handling**: No stack traces in responses
- **Logging**: Comprehensive info/warning/error logs
- **Parallel processing**: ThreadPoolExecutor for concurrent requests
- **Environment variables**: Secure configuration

### ✅ API Endpoints

#### GET /api/news?limit=15
Main endpoint for frontend.

**Request:**
```
GET http://127.0.0.1:5000/api/news?limit=15
```

**Response (Success):**
```json
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
      "source": "CNN",
      "category": "news",
      "published_time": "2025-01-17T10:00:00Z",
      "language": "en"
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "message": "No articles available at this time"
}
```

#### POST /api/extract
Extract full content from a single article URL.

**Request:**
```json
POST http://127.0.0.1:5000/api/extract
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "title": "Article Title",
    "content": "Full article content...",
    "description": "Summary",
    "url": "https://example.com/article",
    "image_url": "https://example.com/image.jpg",
    "language": "en",
    "published_time": "2025-01-17T10:00:00Z"
  }
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "News Aggregation API",
  "version": "2.0.0",
  "redis": "connected",
  "jina": "configured"
}
```

#### GET /
API documentation (root endpoint).

## Setup & Installation

### 1. Install Dependencies

```bash
cd /home/pratik/Desktop/newws/News-Portal

# Install new dependencies
pip install -r requirements-jina.txt
```

**Updated requirements include:**
- `redis==5.0.0` - Redis client (optional)
- `feedparser==6.0.10` - RSS feed parsing

### 2. Set Environment Variables

```bash
# REQUIRED: Get your API key from https://jina.ai
export JINA_API_KEY='your-jina-api-key-here'

# OPTIONAL: Redis configuration
export REDIS_URL='redis://localhost:6379'
export REDIS_ENABLED='true'

# OPTIONAL: Server configuration
export PORT='5000'
export HOST='0.0.0.0'
export DEBUG='False'
```

### 3. Run the Server

```bash
python server_jina.py
```

**Expected output:**
```
2025-01-17 10:00:00 | INFO     | __main__ | ======================================================================
2025-01-17 10:00:00 | INFO     | __main__ | Starting News Aggregation API (v2.0.0)
2025-01-17 10:00:00 | INFO     | __main__ | ======================================================================
2025-01-17 10:00:00 | INFO     | __main__ | Configuration:
2025-01-17 10:00:00 | INFO     | __main__ |   Host: 0.0.0.0
2025-01-17 10:00:00 | INFO     | __main__ |   Port: 5000
2025-01-17 10:00:00 | INFO     | __main__ |   Debug: False
2025-01-17 10:00:00 | INFO     | __main__ |   Jina API: https://r.jina.ai
2025-01-17 10:00:00 | INFO     | __main__ |   Jina Timeout: 30s
2025-01-17 10:00:00 | INFO     | __main__ |   Redis: Enabled
2025-01-17 10:00:00 | INFO     | __main__ |   Cache TTL: 3600s
2025-01-17 10:00:00 | INFO     | __main__ |   Rate Limit: 100 req/60s
2025-01-17 10:00:00 | INFO     | __main__ | ======================================================================
2025-01-17 10:00:00 | INFO     | __main__ | Available endpoints:
2025-01-17 10:00:00 | INFO     | __main__ |   GET  /api/news?limit=15     (Frontend endpoint)
2025-01-17 10:00:00 | INFO     | __main__ |   POST /api/extract           (Single article extraction)
2025-01-17 10:00:00 | INFO     | __main__ |   GET  /health                (Health check)
2025-01-17 10:00:00 | INFO     | __main__ |   GET  /                      (API documentation)
2025-01-17 10:00:00 | INFO     | __main__ | ======================================================================
2025-01-17 10:00:00 | INFO     | __main__ | Server available at:
2025-01-17 10:00:00 | INFO     | __main__ |   http://0.0.0.0:5000/
2025-01-17 10:00:00 | INFO     | __main__ |   http://localhost:5000/
2025-01-17 10:00:00 | INFO     | __main__ |   http://127.0.0.1:5000/
2025-01-17 10:00:00 | INFO     | __main__ | ======================================================================
2025-01-17 10:00:00 | INFO     | __main__ | Initialized 7 news sources
2025-01-17 10:00:00 | INFO     | __main__ | Connected to Redis: redis://localhost:6379
```

### 4. Verify Installation

Test the API:

```bash
# Health check
curl http://127.0.0.1:5000/health

# Get news feed
curl http://127.0.0.1:5000/api/news?limit=5

# Extract single article (replace URL)
curl -X POST http://127.0.0.1:5000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.theguardian.com/world"}'
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JINA_API_KEY` | Required | Jina AI API authentication key |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `REDIS_ENABLED` | `true` | Enable Redis caching |
| `PORT` | `5000` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `DEBUG` | `False` | Debug mode |

### Hard Configuration (in code)

```python
class Config:
    JINA_TIMEOUT = 30                    # Request timeout (seconds)
    JINA_MAX_RETRIES = 2                 # Extraction retry attempts
    API_TIMEOUT = 30                     # Default timeout
    DEFAULT_LIMIT = 15                   # Default articles per request
    MAX_LIMIT = 50                       # Maximum articles per request
    CACHE_TTL = 3600                     # Cache time-to-live (1 hour)
    FEED_REFRESH_INTERVAL = 1800         # Feed refresh interval (30 min)
    MEMORY_CACHE_SIZE = 100              # Max in-memory cache entries
    RATE_LIMIT_REQUESTS = 100            # Rate limit: requests
    RATE_LIMIT_WINDOW = 60               # Rate limit: window (seconds)
```

## Redis Setup (Optional)

### Option 1: Docker (Recommended)

```bash
# Start Redis in Docker
docker run -d -p 6379:6379 redis:latest

# Verify connection
redis-cli ping
# Output: PONG
```

### Option 2: Local Installation

**Linux/Mac:**
```bash
brew install redis  # Mac
sudo apt-get install redis-server  # Ubuntu

redis-server  # Start server
```

**Windows:**
Use WSL2 or Docker Desktop.

### Option 3: Cloud Redis

```bash
# Example: Redis Cloud
export REDIS_URL='redis://default:password@redis-cluster.redis.cloud:port'
```

### Fallback Behavior

If Redis is unavailable:
- System automatically falls back to **in-memory cache**
- No errors exposed to frontend
- All functionality preserved
- Performance slightly degraded (but acceptable)

## Data Flow Explained

### 1. Frontend Request
```
GET /api/news?limit=15
```

### 2. Rate Limiting Check
- Client IP-based token bucket
- Returns 200 with error if limit exceeded
- 100 requests per 60 seconds per IP

### 3. Feed Refresh (if needed)
- Check if 30-minute refresh interval elapsed
- If yes: Fetch articles from 7 RSS feeds in parallel
- If no: Use cached feed

### 4. Article Sorting & Limiting
- Sort by published_time (most recent first)
- Limit to requested count (default 15, max 50)

### 5. Article Enrichment (Parallel)
For each article:
- Generate cache key: `sha256(url)`
- Check Redis cache
- If found: Return cached content
- If not found: Call Jina AI to extract full content
- Retry up to 2 times if failed
- Cache successful extractions (1 hour TTL)
- Return article with full content

### 6. Response to Frontend
```json
{
  "success": true,
  "articles": [...]
}
```

## Monitoring & Debugging

### View Logs

```bash
# Real-time logs
tail -f server_jina.py  # No direct log file yet

# Or with grep for specific levels
python server_jina.py 2>&1 | grep ERROR
python server_jina.py 2>&1 | grep WARNING
```

### Test Endpoints

```bash
# Full workflow test
./test_api.sh  # Create this script

# Individual tests
python -c "
import requests
resp = requests.get('http://127.0.0.1:5000/api/news?limit=5')
print(resp.json())
"
```

### Health Indicators

Check `/health` endpoint:
```json
{
  "status": "ok",
  "redis": "connected",        # Redis operational
  "jina": "configured"         # Jina API key set
}
```

## Production Deployment

### Gunicorn (Recommended)

```bash
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 server_jina:app

# Or with specific configuration
gunicorn \
  --workers=4 \
  --threads=2 \
  --worker-class=gthread \
  --bind 0.0.0.0:5000 \
  --timeout=60 \
  --access-logfile=- \
  --error-logfile=- \
  server_jina:app
```

### Systemd Service (Linux)

Create `/etc/systemd/system/news-api.service`:

```ini
[Unit]
Description=News Aggregation API
After=network.target redis.service

[Service]
Type=notify
User=news
WorkingDirectory=/path/to/News-Portal
Environment="JINA_API_KEY=your_key"
Environment="REDIS_URL=redis://localhost:6379"
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:5000 server_jina:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable news-api
sudo systemctl start news-api
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-jina.txt .
RUN pip install --no-cache-dir -r requirements-jina.txt gunicorn

COPY server_jina.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "server_jina:app"]
```

Build and run:
```bash
docker build -t news-api .
docker run -e JINA_API_KEY=your_key -p 5000:5000 news-api
```

## Performance Considerations

### Latency Breakdown
- Initial RSS feed fetch: ~2-5 seconds (cached for 30 min)
- Per article extraction (Jina): ~2-5 seconds (cached for 1 hour)
- Cache hit: <100ms

### Throughput
- 100 requests/minute per IP (configurable)
- Parallel processing: 3 articles enriched concurrently
- Feed refresh: 5 sources fetched in parallel

### Memory Usage
- In-memory cache: ~10MB (100 articles)
- Process: ~50-100MB
- With Redis: External memory usage

### Optimization Tips
1. Use Redis in production (significant speedup)
2. Adjust `FEED_REFRESH_INTERVAL` if needed (30 min default)
3. Increase `MAX_LIMIT` if frontend needs more articles
4. Use CDN for image caching
5. Monitor Jina API usage (check dashboard)

## Troubleshooting

### Issue: "JINA_API_KEY not configured"

**Solution:**
```bash
export JINA_API_KEY='your-key-here'
python server_jina.py
```

### Issue: "Redis connection failed"

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Verify connection string: `redis://localhost:6379`
3. Server continues working with in-memory cache

### Issue: "No articles available"

**Possible causes:**
- RSS feed endpoints are down
- Network connectivity issue
- Feedparser library issue

**Solution:**
```bash
# Test RSS feeds manually
python -c "
import feedparser
feed = feedparser.parse('http://feeds.reuters.com/reuters/topNews')
print(len(feed.entries))
"
```

### Issue: "Rate limit exceeded"

**Solution:**
- Default limit is 100 req/60s per IP
- Change `RATE_LIMIT_REQUESTS` in Config class
- Or add IP to allowlist in production

### Issue: "Extraction timeout"

**Solution:**
1. Increase `JINA_TIMEOUT` (default 30s)
2. Increase `RATE_LIMIT_WINDOW` to allow slower responses
3. Check Jina API status
4. Some URLs may be unsupported

## Migration from Old Backend

### Breaking Changes
- ❌ **No longer supports** `?url=` parameter for `/api/news`
- ❌ **Old `/api/news` endpoint** completely removed
- ✅ **New endpoint** returns article list, not single article
- ✅ **Frontend compatible** out-of-the-box

### Migration Steps
1. ✅ Already done! Frontend works as-is
2. Update `.env` with `JINA_API_KEY`
3. Install new dependencies: `pip install -r requirements-jina.txt`
4. Stop old server: `pkill -f server.py`
5. Start new server: `python server_jina.py`

### Rollback Plan
Keep old `server.py` as backup:
```bash
git stash  # Save new version
git restore server.py  # Restore old version
```

## API Response Contract

### Frontend Compatibility Checklist

✅ **Endpoint**: `GET /api/news?limit=15`
✅ **Response Code**: Always `200` (no 400/500 errors)
✅ **Response Format**: `{"success": bool, "articles": [...]}`
✅ **Article Fields**: All expected fields present
  - `title`, `headline`, `description`
  - `content`, `url`, `image_url`
  - `source`, `category`, `published_time`, `language`
✅ **No Breaking Changes**: Frontend code unchanged
✅ **CORS**: Properly configured
✅ **Rate Limiting**: Graceful handling

## Support & Debugging

### Enable Debug Mode
```bash
export DEBUG='True'
python server_jina.py
```

### View Detailed Logs
```bash
python server_jina.py 2>&1 | grep -i debug
```

### Test Individual Components

```python
# Test Jina extraction
from server_jina import JinaExtractor, Config
ext = JinaExtractor(Config.JINA_API_KEY)
result, success = ext.extract('https://example.com')
print(result, success)

# Test Redis connection
from server_jina import RedisManager
redis_mgr = RedisManager(Config.REDIS_URL)
redis_mgr.set('test', 'value')
print(redis_mgr.get('test'))

# Test RSS parsing
import feedparser
feed = feedparser.parse('http://feeds.reuters.com/reuters/topNews')
print(f"Found {len(feed.entries)} articles")
```

## License & Attribution

This backend is built with:
- **Jina AI** (https://jina.ai) - Content extraction
- **Feedparser** - RSS parsing
- **Flask** - Web framework
- **Redis** - Caching (optional)

## Contact & Support

For issues:
1. Check this guide
2. Review logs
3. Check Jina API status
4. Verify JINA_API_KEY
5. Test individual components

---

**Version**: 2.0.0  
**Last Updated**: January 17, 2025  
**Status**: Production Ready ✅
