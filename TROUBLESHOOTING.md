# Troubleshooting Guide

## 🔴 Critical Issues

### Issue: Redis Connection Failed

**Symptom:**
```
⚠ Redis connection failed: [Errno 111] Connection refused
Using in-memory fallback
```

**Root Cause:**
- Redis server not running
- Wrong Redis URL configured
- Redis port blocked

**Solution:**

```bash
# 1. Check if Redis is running
redis-cli ping

# 2. If not running, start it
sudo systemctl start redis-server

# 3. Or start manually
redis-server --daemonize yes

# 4. Verify connection
redis-cli ping  # Should output: PONG

# 5. Check Redis URL
echo $REDIS_URL  # Should be: redis://localhost:6379

# 6. Test from Python
python3 -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

**Fallback Status:**
- In-memory cache will be used (slower than Redis)
- Still works, but limited to current process memory
- No persistence across restarts
- ✓ Safe to proceed

---

### Issue: API Responding Slowly (TTFB >200ms)

**Symptom:**
```
First request taking 500ms+
Repeat requests slow
```

**Root Cause Analysis:**

1. **Jina AI extraction slow**
   ```bash
   # Test Jina response time
   time curl -H "Authorization: Bearer $JINA_API_KEY" \
     "https://r.jina.ai/https://example.com"
   ```
   - Normal: <500ms
   - Slow: >1000ms
   - Network issue likely

2. **Redis lookup slow**
   ```bash
   # Test Redis latency
   redis-cli --latency-history
   ```
   - Normal: <1ms
   - Slow: >10ms
   - Memory pressure or disk I/O

3. **Server under load**
   ```bash
   # Check CPU/memory
   top -bn1 | grep server_production
   ```
   - CPU: Should be <50%
   - Memory: Should be <500MB

**Solutions:**

```bash
# For Jina issues:
# - Check network connectivity
# - Use VPN if Jina blocked
# - Try alternate extraction service

# For Redis issues:
# - Restart Redis: redis-cli SHUTDOWN; redis-server --daemonize yes
# - Check disk space: df -h
# - Monitor live: redis-cli MONITOR

# For server load:
# - Check running processes: ps aux | grep python
# - Monitor threads: lsof -p $(pgrep server_production)
# - Scale horizontally with Gunicorn workers
```

---

### Issue: TTFB Getting Slower Over Time

**Symptom:**
```
Hour 1: Average TTFB 20ms
Hour 6: Average TTFB 150ms
```

**Root Cause:**
- Redis memory full
- Cache hit rate decreasing
- Disk swapping

**Solution:**

```bash
# 1. Check Redis memory
redis-cli INFO memory
```

Output:
```
# Memory
used_memory: 500MB
used_memory_human: 500.00M
maxmemory: 2GB  ← If near maxmemory, cache evicting
```

```bash
# 2. If approaching limit, increase Redis memory
# Edit /etc/redis/redis.conf:
# maxmemory 2gb  ← Increase if needed

# 3. Check what's consuming memory
redis-cli MEMORY USAGE "article:*:content"

# 4. Manual cache cleanup
redis-cli FLUSHDB  ← CAUTION: Clears all cache

# 5. Monitor memory in real-time
redis-cli MONITOR | grep MEMORY
```

---

## ⚠️ Warning Issues

### Issue: Image Not Updating

**Symptom:**
```
Image stays as placeholder
Browser console shows continuous polling
After 6 minutes: polling stops, image still placeholder
```

**Root Cause:**
- Gemini API key not configured
- Gemini API rate limited
- Image generation timeout

**Solution:**

```bash
# 1. Verify Gemini key is set
echo $GEMINI_API_KEY  # Should not be empty

# 2. Test Gemini directly
python3 -c "
import google.generativeai as genai
genai.configure(api_key='$GEMINI_API_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Test prompt')
print('✓ Gemini working')
"

# 3. Check for rate limiting errors
tail -f logs/server.log | grep -i "rate\|limit\|429"

# 4. Monitor background threads
ps aux | grep -i "imagegen\|generation"

# 5. Check Redis for image cache
redis-cli KEYS "article:*:image" | head -20
```

**Fallback:**
- If Gemini unavailable, image stays as placeholder
- User still sees text content
- ✓ Acceptable fallback

---

### Issue: "Rate Limit Exceeded" Errors

**Symptom:**
```
{
  "success": false,
  "message": "Rate limit exceeded"
}
```

**Root Cause:**
- >200 requests per 60 seconds from single IP
- Testing script generating too many requests
- DDoS-like behavior

**Solution:**

```bash
# 1. Check rate limiter settings
grep "RATE_LIMIT" server_production.py

# 2. If testing, use delays
python3 test_performance.py  # Already has delays built-in

# 3. Increase limit if needed
# Edit server_production.py:
# RATE_LIMIT_REQUESTS = 200  ← Increase to 500
# Then restart server

# 4. For production, use reverse proxy rate limiting:
# nginx rate_limit directive
# CDN rate limiting
```

---

### Issue: "JINA_API_KEY not set" Warnings

**Symptom:**
```
✗ Jina extraction failed: Missing JINA_API_KEY
Article content extraction disabled
```

**Root Cause:**
- Environment variable not set
- Wrong variable name
- Shell not properly configured

**Solution:**

```bash
# 1. Get Jina API key from https://jina.ai

# 2. Set it permanently in shell
export JINA_API_KEY="jina_xxxxxxxxxxxxx"

# 3. Verify it's set
echo $JINA_API_KEY

# 4. For permanent setting, add to ~/.bashrc
echo 'export JINA_API_KEY="jina_xxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc

# 5. For system-wide, create .env file
cat > .env << EOF
JINA_API_KEY=jina_xxxxxxxxxxxxx
GEMINI_API_KEY=sk-xxxxxxxxxxxxx
REDIS_URL=redis://localhost:6379
EOF

# 6. Load from .env when starting
source .env && python3 server_production.py
```

---

## 🟡 Performance Issues

### Issue: High TTFB on First Request

**Expected:** ~150ms
**Actual:** ~800ms

**Diagnosis:**

```bash
# 1. Measure Jina extraction time
python3 -c "
import requests, time
start = time.time()
response = requests.get(
    'https://r.jina.ai/https://www.bbc.com/news',
    headers={'Authorization': f'Bearer \$JINA_API_KEY'},
    timeout=30
)
elapsed = (time.time() - start) * 1000
print(f'Jina extraction: {elapsed:.0f}ms')
"

# 2. Check network latency to Jina
ping -c 5 r.jina.ai

# 3. Test API response time
time curl -H "Authorization: Bearer $JINA_API_KEY" \
  https://r.jina.ai/https://example.com > /dev/null
```

**Solutions:**

| Issue | TTFB | Solution |
|-------|------|----------|
| Network latency to Jina | 200-500ms | Use VPN, check ISP, cache more |
| Jina API slow | 500-1000ms | Check Jina status, try later |
| Server processing | 100-200ms | Optimize Flask, add workers |
| Combined slow | 1000ms+ | Use all above + Gunicorn workers |

```bash
# Scale with Gunicorn
gunicorn -w 8 -b 0.0.0.0:5000 \
  --worker-class sync \
  --timeout 30 \
  server_production:app
```

---

### Issue: Cached Requests Still Slow (>50ms)

**Expected:** <50ms
**Actual:** >100ms

**Diagnosis:**

```bash
# 1. Check Redis latency
redis-cli --latency

# 2. Monitor Redis commands
redis-cli MONITOR

# 3. Check Redis memory
redis-cli INFO memory | grep used

# 4. Check Python GIL contention
python3 -c "import sys; print(f'GIL optimization: {sys.flags.optimizeFlag}')"
```

**Solutions:**

```bash
# For Redis latency issues:
redis-cli SLOWLOG GET 10  # Show slow commands

# Restart Redis clean
redis-cli SHUTDOWN
redis-server --daemonize yes --maxmemory 2gb

# For server concurrency:
# Use Gunicorn with multiple workers
gunicorn -w 4 --worker-class sync server_production:app

# For high load:
# Add caching layer (nginx)
# Add monitoring (Prometheus)
# Add load balancing
```

---

## 🟠 Debugging

### Enable Verbose Logging

```python
# In server_production.py:
import logging

# Set to DEBUG
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Restart server
python3 server_production.py
```

### Monitor All Cache Operations

```bash
# Watch Redis commands
redis-cli MONITOR | grep -E "GET|SET|DEL"

# Count cache keys by type
redis-cli KEYS "article:*:content" | wc -l
redis-cli KEYS "article:*:summary" | wc -l
redis-cli KEYS "article:*:image" | wc -l

# Get total cache size
redis-cli DEBUG OBJECT "article:hash:content"
```

### Test Individual Components

```bash
# Test Jina
python3 << 'EOF'
from server_production import extract_article_jina
result = extract_article_jina("https://example.com")
print(f"✓ Jina working: {bool(result)}")
EOF

# Test Gemini
python3 << 'EOF'
from server_production import generate_summary_gemini
result = generate_summary_gemini("Test content here")
print(f"✓ Gemini summary: {result[:50]}...")
EOF

# Test Redis
python3 << 'EOF'
from redis_cache import get_redis_cache
cache = get_redis_cache()
print(f"✓ Redis status: {cache.health_check()}")
EOF
```

---

## 🟢 Verification Tests

### Quick Health Check

```bash
#!/bin/bash
# Run this to verify everything is working

echo "🔍 System Health Check"
echo "===================="

# 1. Redis
echo -n "✓ Redis: "
redis-cli ping > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# 2. Backend
echo -n "✓ Backend: "
curl -s http://127.0.0.1:5000/health > /dev/null && echo "OK" || echo "FAILED"

# 3. API
echo -n "✓ API: "
RESPONSE=$(curl -s "http://127.0.0.1:5000/api/article?url=https://example.com")
echo "$RESPONSE" | grep -q "success" && echo "OK" || echo "FAILED"

# 4. Cache
echo -n "✓ Cache: "
KEYS=$(redis-cli DBSIZE | awk '{print $2}')
echo "$KEYS keys"

# 5. Frontend
echo -n "✓ Frontend: "
curl -s http://127.0.0.1:8000 > /dev/null && echo "OK" || echo "FAILED"

echo "===================="
echo "✓ Health check complete"
```

### Performance Benchmark

```bash
#!/bin/bash
# Measure current performance

echo "📊 Performance Test"
echo "=================="

# Test 1: First request
echo -n "First request TTFB: "
curl -w "%{time_total}\n" -o /dev/null -s \
  "http://127.0.0.1:5000/api/article?url=https://example.com" \
  | awk '{print $1*1000" ms"}'

# Test 2: Cached request
echo -n "Cached request TTFB: "
curl -w "%{time_total}\n" -o /dev/null -s \
  "http://127.0.0.1:5000/api/article?url=https://example.com" \
  | awk '{print $1*1000" ms"}'

# Test 3: Concurrent (5 requests)
echo -n "5 concurrent requests: "
for i in {1..5}; do
  curl -s "http://127.0.0.1:5000/api/article?url=https://example.com" &
done
wait
echo "✓ Completed"

echo "=================="
```

---

## 📞 Getting Help

### Check Logs

```bash
# Server logs
tail -f logs/server.log

# Full log with timestamps
less logs/server.log

# Search for errors
grep -i "error\|failed" logs/server.log

# Last 50 lines
tail -50 logs/server.log
```

### Debug Output

```bash
# Run with debug output
DEBUG=true python3 server_production.py

# Run with profiling
python3 -m cProfile -s cumulative server_production.py

# Run with verbose logging
PYTHONVERBOSE=2 python3 server_production.py
```

### Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| Gemini rate limited | Wait 60s, increase key limit |
| Jina extraction timeout | Increase TIMEOUT, retry article |
| Redis out of memory | Increase maxmemory, clear cache |
| Image not generating | Check Gemini key, restart backend |
| Cache hit rate low | Wait longer, cache more articles |
| TTFB still high | Scale with Gunicorn, add workers |

---

## ✅ Success Verification

When everything is working:

```bash
# 1. API responds fast
curl -w "TTFB: %{time_total}s\n" http://127.0.0.1:5000/health
# Should show: TTFB: 0.020s (20ms)

# 2. Cache growing
redis-cli DBSIZE
# Should show: (integer) 50+

# 3. Logs show progress
tail -f logs/server.log
# Should show: ✓ Article response: 150.2ms

# 4. Concurrent requests work
ab -n 100 -c 10 http://127.0.0.1:5000/health
# Should show: Requests/sec: 1000+

# 5. No errors
grep -i "error\|failed" logs/server.log
# Should show: (nothing)
```

---

**Everything working? You're production ready!** 🚀
