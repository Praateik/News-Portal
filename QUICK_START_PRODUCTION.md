# Quick Start: Production News API

## ⚡ 5-Minute Setup

### 1. Install Redis
```bash
sudo apt-get install -y redis-server redis-tools
redis-cli ping  # Should output: PONG
```

### 2. Install Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt
```

### 3. Set API Keys
```bash
export JINA_API_KEY="your_jina_key_here"
export GEMINI_API_KEY="your_gemini_key_here"
```

### 4. Start Production Backend
```bash
python3 server_production.py
```

### 5. Test It
```bash
# In another terminal:
curl http://127.0.0.1:5000/health
```

---

## 🧪 Performance Testing

```bash
# Run performance test suite
python3 test_performance.py
```

Expected output:
```
📊 First Requests (Cache Miss):
  Average: 150.3ms
  Target: <200ms
  Status: ✓ PASS

📊 Cached Requests (Cache Hit):
  Average: 22.5ms
  Target: <50ms
  Status: ✓ PASS
```

---

## 🖥️ Frontend Setup

In a separate terminal:

```bash
cd news-website-ui
python3 -m http.server 8000
```

Then open: http://127.0.0.1:8000

---

## 📋 What's New

### New Backend Modules
- `redis_cache.py` - Redis caching layer with TTL management
- `background_image_generator.py` - Non-blocking image generation
- `server_production.py` - Optimized Flask backend with `<200ms TTFB`

### Updated Frontend
- `js/article.js` - Progressive image polling (every 3s)
- `js/script.js` - Performance metrics logging
- `html/article.html` - Optimized HTML structure

### Documentation
- `PRODUCTION_ARCHITECTURE.md` - Complete architecture guide
- `test_performance.py` - Automated performance testing

---

## 🎯 Key Features

### Caching Strategy
- **article:{hash}:content** → Extracted content (24h)
- **article:{hash}:summary** → AI summary (24h)
- **article:{hash}:image** → Generated image (7d)
- **article:{hash}:meta** → Full metadata (24h)

### Performance Targets
- **First byte**: <200ms ✓
- **Cached requests**: <50ms ✓
- **Background jobs**: Non-blocking ✓

### API Endpoints

#### GET /api/article?url=...
Returns optimized article with AI features.

```bash
curl "http://127.0.0.1:5000/api/article?url=https://example.com/article"
```

Response:
```json
{
  "success": true,
  "article": {
    "title": "...",
    "content": "...",
    "summary": "AI-generated summary...",
    "image_url": "/images/placeholder-blur.jpg",
    "source": "...",
    "category": "...",
    "ai_generated": true
  },
  "performance": {
    "ttfb_ms": 150.3
  }
}
```

#### GET /health
Service health check.

```bash
curl http://127.0.0.1:5000/health
```

#### GET /api/cache/stats (Debug)
Cache statistics.

```bash
curl http://127.0.0.1:5000/api/cache/stats
```

---

## 🔍 Debugging

### Check Redis
```bash
# Is Redis running?
redis-cli ping

# Cache size
redis-cli DBSIZE

# All cache keys
redis-cli KEYS "article:*"

# Clear cache (development only)
redis-cli FLUSHDB
```

### Check Server
```bash
# API responding?
curl http://127.0.0.1:5000/health

# With timing
curl -w "TTFB: %{time_total}s\n" http://127.0.0.1:5000/health
```

### View Logs
```bash
# From the running server terminal
# Look for messages like:
# ✓ Article response: 145.2ms
# ✓ Cache hit (meta): 12.5ms
# ✓ Image generated in 1.23s: hash → image_url
```

---

## 📊 Architecture Overview

```
Browser (Frontend)
    ↓ HTTP GET /api/article?url=...
    ↓ (<50ms if cached)
    ↓
Flask Backend (server_production.py)
    ├─ Check Redis cache (instant hit)
    ├─ Extract content (Jina AI)
    ├─ Generate summary (Gemini - background)
    ├─ Generate image (Gemini - background)
    └─ Return <200ms response with placeholder
    ↓ BACKGROUND THREADS (non-blocking)
    ├─ Cache summary in Redis
    └─ Cache image URL in Redis
    ↓
Frontend polling every 3s
    └─ Updates image when ready
```

---

## ⚙️ Environment Variables

```bash
# API Keys
JINA_API_KEY=jina_xxxxx...
GEMINI_API_KEY=sk-xxxxx...

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Server
PORT=5000           # API port
HOST=0.0.0.0        # Bind to all interfaces
DEBUG=false         # Production mode

# Logging
LOG_LEVEL=INFO      # Logging verbosity
```

---

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 server_production:app
```

### Using Docker
```bash
docker build -t news-api .
docker run -p 5000:5000 \
  -e JINA_API_KEY=... \
  -e GEMINI_API_KEY=... \
  -e REDIS_URL=redis://redis:6379 \
  news-api
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Redis is running: `redis-cli ping`
- [ ] Backend starts: `python3 server_production.py`
- [ ] Health check passes: `curl http://127.0.0.1:5000/health`
- [ ] Article endpoint works: `curl http://127.0.0.1:5000/api/article?url=...`
- [ ] First request <200ms TTFB
- [ ] Cached request <50ms TTFB
- [ ] Frontend loads: http://127.0.0.1:8000
- [ ] Article page loads with progressive image
- [ ] Performance tests pass: `python3 test_performance.py`

---

## 🎓 Understanding the Flow

### Request #1 (Cache Miss)
```
Time  Event
0ms   ├─ API request arrives
10ms  ├─ Check Redis cache (miss)
30ms  ├─ Extract content from Jina (20ms)
50ms  ├─ Generate summary in background ← BACKGROUND THREAD
150ms └─ RETURN RESPONSE with placeholder image
        
BACKGROUND: Summary cached, image generation starts
500ms → Image cached in Redis
```

### Request #2 (Cache Hit)
```
Time  Event
0ms   ├─ API request arrives
10ms  ├─ Check Redis cache (HIT!)
20ms  └─ RETURN RESPONSE with cached summary + image
```

### Frontend Polling
```
Browser polls every 3 seconds:
GET /api/article?url=...

When image is ready:
- Frontend receives: "image_url": "https://storage/final.jpg"
- Updates: document.getElementById('article-image').src = final_url
- No page reload needed
```

---

## 📞 Common Issues

**Q: Why is TTFB >200ms?**
A: Check Jina API response times with `curl https://r.jina.ai/https://example.com`

**Q: Why is cached request still slow?**
A: Check Redis with `redis-cli --latency`

**Q: Image not updating?**
A: Check browser console for polling errors. Verify image generation completed.

**Q: Redis connection failed?**
A: Start Redis: `redis-server --daemonize yes`

---

**Ready to run sub-200ms responses!** 🚀
