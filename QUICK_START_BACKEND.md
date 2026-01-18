# Quick Start: Production News Backend

## 30-Second Setup

```bash
# 1. Install dependencies
pip install -r requirements-jina.txt

# 2. Set API key (required)
export JINA_API_KEY='your-key-from-jina.ai'

# 3. Run server
python server_jina.py

# 4. Test it
curl http://127.0.0.1:5000/api/news?limit=5
```

## What Changed

### ✅ Frontend Works Out-of-Box
- Existing frontend needs **zero changes**
- Old `?url=` parameter requirement **removed**
- Returns article **list** instead of single article

### ✅ API Compatibility
```javascript
// Frontend calls this (unchanged)
fetch('http://127.0.0.1:5000/api/news?limit=15')

// Gets this format (correct for 2025 frontend)
{
  "success": true,
  "articles": [
    {
      "title": "...",
      "headline": "...",
      "description": "...",
      "content": "...",
      "url": "...",
      "image_url": "...",
      "source": "...",
      "category": "...",
      "published_time": "...",
      "language": "..."
    }
  ]
}
```

## Architecture

```
Frontend (news-website-ui)
    ↓
GET /api/news?limit=15
    ↓
┌─────────────────────────────────────┐
│ NewsFeedManager                     │
│  ├─ Fetches 7 RSS feeds (parallel) │
│  ├─ Sorts by date                  │
│  └─ Enriches with Jina AI          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ JinaExtractor                       │
│  ├─ Calls r.jina.ai                │
│  ├─ Extracts full content          │
│  ├─ Retries 2x on failure          │
│  └─ Caches results (1 hour)        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ RedisManager (with fallback)        │
│  ├─ Primary: Redis cache           │
│  └─ Fallback: In-memory cache      │
└─────────────────────────────────────┘
    ↓
Return 15 articles to frontend
```

## Key Features Delivered

| Feature | Status | Details |
|---------|--------|---------|
| Frontend compatible | ✅ | Works without any changes |
| RSS aggregation | ✅ | 7 feeds, parallel fetch |
| Jina AI extraction | ✅ | Full article content |
| Redis caching | ✅ | Optional with fallback |
| Error handling | ✅ | No 400 errors, graceful fails |
| Rate limiting | ✅ | 100 req/60s per IP |
| CORS | ✅ | localhost only |
| Production ready | ✅ | Logging, health check, metrics |

## Configuration

### Required
```bash
export JINA_API_KEY='your-api-key'
```

### Optional
```bash
export REDIS_URL='redis://localhost:6379'    # For caching
export PORT='5000'                            # Server port
export HOST='0.0.0.0'                        # Server host
export DEBUG='False'                          # Debug mode
```

## Testing

### 1. Health Check
```bash
curl http://127.0.0.1:5000/health
```

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

### 2. Get News Feed
```bash
curl http://127.0.0.1:5000/api/news?limit=5
```

### 3. Extract Single Article
```bash
curl -X POST http://127.0.0.1:5000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.theguardian.com/world/latest"
  }'
```

## News Sources

Automatically fetched from these RSS feeds:

1. **Reuters Top News** - `http://feeds.reuters.com/reuters/topNews`
2. **BBC News** - `http://feeds.bbci.co.uk/news/rss.xml`
3. **The Guardian** - `https://www.theguardian.com/world/rss`
4. **TechCrunch** - `http://feeds.techcrunch.com/TechCrunch/`
5. **Hacker News** - `https://news.ycombinator.com/rss`
6. **ESPN** - `https://www.espn.com/espn/rss/news`
7. **Reuters Entertainment** - `http://feeds.reuters.com/reuters/entertainmentNews`

### Add More Sources

Edit `NewsFeedManager._init_sources()` in `server_jina.py`:

```python
self.sources = [
    # Existing sources...
    NewsSource('Your Source', 'https://example.com/rss', 'news'),
]
```

## Performance

| Metric | Value |
|--------|-------|
| First request (no cache) | ~5-10s |
| Subsequent requests | ~100ms (cached) |
| Feed refresh interval | 30 minutes |
| Article cache TTL | 1 hour |
| Rate limit | 100 req/60s per IP |
| Max articles per request | 50 |
| Default articles | 15 |

## Common Issues & Fixes

### "JINA_API_KEY not configured"
```bash
export JINA_API_KEY='your-key'
python server_jina.py
```

### "Redis connection failed"
- Server will automatically use in-memory cache
- No action needed, system still works
- Restart Redis: `redis-server`

### "No articles available"
- Check RSS feeds are accessible
- Wait 30 minutes for next refresh cycle
- Or force refresh by restarting server

### Rate limited
- Default: 100 requests per 60 seconds per IP
- Wait a minute or increase limit in Config

## Production Deployment

### With Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 server_jina:app
```

### With Docker

```bash
docker build -t news-api .
docker run -e JINA_API_KEY=your_key -p 5000:5000 news-api
```

### With Systemd

See full guide in `PRODUCTION_BACKEND_GUIDE.md`

## File Structure

```
News-Portal/
├── server_jina.py              # Production backend (NEW!)
├── requirements-jina.txt       # Dependencies (UPDATED)
├── PRODUCTION_BACKEND_GUIDE.md # Full documentation (NEW!)
├── QUICK_START.md              # This file (NEW!)
└── news-website-ui/            # Frontend (unchanged)
    ├── index.html
    ├── js/script.js            # Calls GET /api/news?limit=15
    └── ...
```

## Next Steps

1. ✅ Get JINA_API_KEY from https://jina.ai
2. ✅ Install dependencies: `pip install -r requirements-jina.txt`
3. ✅ Set environment: `export JINA_API_KEY='...'`
4. ✅ Run server: `python server_jina.py`
5. ✅ Open frontend: `http://127.0.0.1:8000` (or your UI server)
6. ✅ Articles load automatically!

## Support

For detailed setup, troubleshooting, and production deployment:
→ See `PRODUCTION_BACKEND_GUIDE.md`

---

**Status**: ✅ Production Ready  
**Version**: 2.0.0  
**Updated**: January 17, 2025
