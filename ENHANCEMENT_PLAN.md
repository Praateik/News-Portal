# Nepal Times News Aggregator - Enhancement Plan

## 📋 Current State Analysis

### ✅ What's Already Built:
- Flask backend with RSS and homepage scraping
- Article extraction using news-fetch library
- Hourly automatic updates with APScheduler
- Basic duplicate detection (text similarity)
- Featured news promotion
- Puter.js frontend with on-demand image generation
- Internal article pages (no external redirects)

### ❌ What's Missing (per requirements):
1. **robots.txt compliance & rate limiting**
2. **Language detection (especially Devanagari)**
3. **On-demand LLM summarization** (currently simple extraction)
4. **Proper deduplication with SHA256 hashing**
5. **Database persistence** (currently in-memory)
6. **Summary caching** (no Redis/cache)
7. **Production-ready error handling**
8. **API endpoints for on-demand summaries**
9. **Security & rate limiting**

---

## 🎯 Enhancement Plan

### Phase 1: Backend Architecture (Priority: HIGH)
- [ ] **database_schema.py** - PostgreSQL schema with proper indexes
- [ ] **config.yaml** - Centralized configuration
- [ ] **scraper_enhanced.py** - Scalable scraper with:
  - robots.txt compliance
  - Rate limiting per domain
  - SHA256 hashing for deduplication
  - Language detection (fastText)
  - Async fetching with retries
- [ ] **models.py** - SQLAlchemy ORM models
- [ ] **celery_config.py** - Celery for background tasks

### Phase 2: AI Summarization (Priority: HIGH)
- [ ] **summarizer_service.py** - On-demand LLM summarization
- [ ] **language_detector.py** - fastText-based language detection
- [ ] **prompt_templates.py** - Language-specific summarization prompts
- [ ] **summary_cache.py** - Redis-based caching for summaries

### Phase 3: API Enhancement (Priority: MEDIUM)
- [ ] **api_v2.py** - New FastAPI-based API with:
  - GET /api/v2/articles (paginated, filtered)
  - GET /api/v2/articles/{id}/summary (on-demand)
  - POST /api/v2/summarize (batch)
  - Rate limiting middleware
- [ ] **schemas.py** - Pydantic models for API

### Phase 4: Frontend Enhancement (Priority: MEDIUM)
- [ ] **modern_article_page.html** - SEO-friendly article display
- [ ] **summary_component.js** - On-demand summary fetching
- [ ] **lazy_image_handler.js** - Optimized image loading
- [ ] **service_worker.js** - PWA support for offline reading

### Phase 5: DevOps & Monitoring (Priority: LOW)
- [ ] **Dockerfile** - Containerized deployment
- [ ] **docker-compose.yml** - Multi-service setup
- [ ] **monitoring/** - Prometheus metrics + Grafana dashboards
- [ ] **logging_config.py** - Structured JSON logging

---

## 🔧 Implementation Details

### 1. Database Schema (PostgreSQL)

```sql
-- Sources table
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    base_url VARCHAR(500),
    rss_url VARCHAR(500),
    parser_type VARCHAR(50),  -- 'rss', 'soup', 'playwright'
    rate_limit_requests INT DEFAULT 10,
    rate_limit_seconds INT DEFAULT 60,
    robots_txt_allowed BOOLEAN DEFAULT TRUE,
    last_fetched TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Articles table
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    url VARCHAR(1000) UNIQUE NOT NULL,
    url_hash SHA256,
    headline VARCHAR(500),
    description TEXT,
    raw_text TEXT,
    article_text TEXT,
    language VARCHAR(10),  -- 'ne', 'en', 'hi', etc.
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW(),
    image_url VARCHAR(1000),
    category VARCHAR(100),
    author VARCHAR(200),
    metadata JSONB,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES articles(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_articles_url_hash ON articles(url_hash);
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_language ON articles(language);
CREATE INDEX idx_articles_source ON articles(source_id);

-- Summaries table
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    summary_text TEXT NOT NULL,
    model VARCHAR(100),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    cached_until TIMESTAMP
);

CREATE INDEX idx_summaries_article ON summaries(article_id, language);

-- Images table
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    original_url VARCHAR(1000),
    storage_path VARCHAR(500),
    width INTEGER,
    height INTEGER,
    attribution TEXT,
    license_info TEXT,
    checksum VARCHAR(64)
);
```

### 2. Scraper Architecture

```
scraper/
├── __init__.py
├── base.py           # BaseScraper abstract class
├── rss_scraper.py    # RSS feed parser
├── soup_scraper.py   # BeautifulSoup-based scraper
├── playwright_scraper.py  # JS-rendered pages
├── robots.py         # robots.txt compliance
├── rate_limiter.py   # Token bucket rate limiter
├── dedup.py          # SHA256 + SimHash deduplication
├── language.py       # fastText language detection
└── __main__.py       # Entry point
```

### 3. Summarization Service

```
summarizer/
├── __init__.py
├── base.py           # BaseSummarizer
├── llm_summarizer.py # LLM-based summarization
├── cache.py          # Redis cache wrapper
├── prompts.py        # Language-specific prompts
└── __main__.py       # CLI tool
```

### 4. API Endpoints (FastAPI)

```python
# New endpoints to add
GET /api/v2/articles?source=all&lang=ne&limit=20&offset=0
GET /api/v2/articles/{id}
GET /api/v2/articles/{id}/summary?lang=auto  # On-demand
POST /api/v2/articles/{id}/summarize          # Trigger summarization
GET /api/v2/sources
GET /api/v2/health
```

---

## 📝 Code Quality Standards

1. **Type Hints** - All functions must have type annotations
2. **Docstrings** - Google-style docstrings for all public functions
3. **Error Handling** - Structured exceptions with context
4. **Logging** - JSON-structured logs with correlation IDs
5. **Tests** - Unit tests for core functions (pytest)
6. **Security** - Input validation, rate limiting, sanitization

---

## 🚫 What I CANNOT Implement (Legal Boundaries)

1. **❌ Bypassing robots.txt** - Must respect site rules
2. **❌ Removing watermarks** - Must preserve original images with attribution
3. **❌ Aggressive scraping** - Must have rate limits

### ✅ Legal Alternatives:
- Use `robots.txt` compliance layer
- Store original images with visible attribution
- Use licensed images or request permission
- Implement polite scraping with delays

---

## 📦 Deliverables (by priority)

1. **Week 1**: Backend enhancement (scraper, DB, dedup)
2. **Week 2**: AI summarization service
3. **Week 3**: API & frontend improvements
4. **Week 4**: DevOps, monitoring, testing

---

## 🔍 Next Steps

**Choose one to start:**
- A) Database schema + models (foundation layer)
- B) Enhanced scraper with rate limiting (core functionality)
- C) LLM summarization service (AI features)
- D) FastAPI endpoints (API layer)
- E) Frontend enhancements (UI/UX)

Or say "All" and I'll implement sequentially starting with A.

