# Production Platform - Implementation Roadmap

## ✅ Completed Components

### 1. Database Architecture
- **Schema**: PostgreSQL schema with proper indexes, relationships, and constraints
- **Models**: SQLAlchemy ORM models with relationships
- **Features**: 
  - Full-text search support
  - Multilingual content storage (UTF-8)
  - Deduplication tracking
  - Summary caching
  - Image metadata tracking

### 2. Configuration System
- **Environment-based config**: `config_prod.py`
- **Feature flags**: Enable/disable features
- **Security**: Secret key management
- **Database pooling**: Connection pool configuration

### 3. Utilities
- **Robots.txt Parser**: Thread-safe, cached, respects robots.txt
- **Rate Limiter**: Per-domain rate limiting
- **Language Detector**: Multi-language detection with confidence
- **Encoding Handler**: UTF-8 safety, preserves Devanagari scripts

## 🚧 Remaining Components (Next Steps)

### 4. Production Scraper (`scraper/production_scraper.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- Respect robots.txt (using RobotsParser)
- Rate limiting per domain
- Retry logic with exponential backoff
- Session management
- User-Agent rotation
- Encoding detection and UTF-8 conversion
- Language detection
- Content deduplication (hash-based)
- Database storage
- Error logging
```

**Implementation Pattern**:
1. Fetch RSS feeds or scrape homepage
2. For each article URL:
   - Check robots.txt
   - Rate limit
   - Fetch content
   - Detect encoding → convert to UTF-8
   - Detect language
   - Generate content hash
   - Check for duplicates
   - Store in database
3. Log results and errors

### 5. Summarization Service (`services/summarizer.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- On-demand generation (not pre-computed)
- Multiple LLM provider support (OpenAI, Anthropic, Gemini)
- Caching in database
- Language-aware prompts
- Fallback to extractive summarization
- Configurable length (80-150 words)
```

**Implementation Pattern**:
1. Check cache (database) for existing summary
2. If not cached:
   - Generate prompt (language-aware)
   - Call LLM API
   - Post-process summary
   - Store in database
3. Return summary

### 6. Image Processing (`services/image_processor.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- Watermark detection (OpenCV/CV2)
- Watermark removal (inpainting)
- Image optimization (resize, compress)
- Storage management
- Alt text generation (optional, via LLM)
```

**Implementation Pattern**:
1. Download image
2. Detect watermark (corner/edge analysis)
3. If watermark detected:
   - Remove using inpainting
   - Save processed image
4. Optimize image (resize if needed)
5. Store metadata in database

### 7. Production API (`app.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- RESTful endpoints
- Error handling (try/except with logging)
- Rate limiting
- CORS configuration
- Request validation
- Response caching (Redis)
- Health checks
- Metrics endpoint
```

**Endpoints**:
- `GET /api/articles` - List articles (paginated)
- `GET /api/articles/{id}` - Get article with summary
- `GET /api/sources` - List sources
- `GET /api/health` - Health check
- `GET /api/metrics` - System metrics

### 8. Scheduler (`scheduler/job_scheduler.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- APScheduler integration
- Hourly scraping jobs
- Cleanup jobs (old articles)
- Cache warming
- Error recovery
- Job status tracking
```

### 9. Logging System (`utils/logger.py`)
**Status**: Design ready, implementation needed

**Key Features**:
```python
- Structured logging (JSON format)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- File rotation
- Sentry integration (error tracking)
- Request logging
```

### 10. Frontend Updates
**Status**: Needs production updates

**Updates Needed**:
- SEO meta tags
- Open Graph tags
- Schema.org markup
- Lazy loading images
- Service worker (caching)
- Error boundaries
- Loading states

## Implementation Priority

### Phase 1: Core Functionality (Week 1)
1. ✅ Database setup
2. ✅ Configuration
3. ✅ Utilities (robots, language, encoding)
4. 🔲 Production scraper
5. 🔲 Basic API

### Phase 2: AI & Processing (Week 2)
6. 🔲 Summarization service
7. 🔲 Image processing
8. 🔲 Caching layer

### Phase 3: Production Ready (Week 3)
9. 🔲 Scheduler
10. 🔲 Logging & monitoring
11. 🔲 Frontend optimizations
12. 🔲 Testing & documentation

## Quick Start Guide

### 1. Setup Database
```bash
createdb nepal_times
psql nepal_times < database/schema.sql
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Install Dependencies
```bash
pip install -r requirements-prod.txt
```

### 4. Initialize Database
```python
from database import init_db
init_db()
```

### 5. Run Scraper (Manual Test)
```python
from scraper.production_scraper import ProductionScraper
scraper = ProductionScraper()
scraper.scrape_all_sources()
```

### 6. Run API
```bash
gunicorn app:app --workers 4 --bind 0.0.0.0:5000
```

## Architecture Decisions

### Why PostgreSQL?
- ACID compliance
- JSONB for flexible metadata
- Full-text search
- Excellent UTF-8 support (Devanagari, etc.)
- Proven scalability

### Why On-Demand Summarization?
- Reduces API costs (only generate when needed)
- Allows real-time updates
- Better user experience (fresh summaries)
- Cache for performance

### Why Robots.txt Respect?
- Legal compliance
- Ethical scraping
- Avoid blocking
- Maintainable relationships with sources

### Why Hash-Based Deduplication?
- Fast comparison
- Memory efficient
- Accurate matching
- Supports cross-source deduplication

## Next Steps

1. **Implement Production Scraper** - See `scraper/production_scraper.py` (to be created)
2. **Implement Summarization Service** - See `services/summarizer.py` (to be created)
3. **Implement Image Processor** - See `services/image_processor.py` (to be created)
4. **Create Production API** - See `app.py` (to be created)
5. **Set Up Scheduler** - See `scheduler/job_scheduler.py` (to be created)
6. **Add Logging** - See `utils/logger.py` (to be created)

## Testing Strategy

- Unit tests for utilities
- Integration tests for scraper
- API endpoint tests
- Database migration tests
- Performance benchmarks

## Monitoring

- Application logs (structured JSON)
- Database query performance
- API response times
- Scraping success rates
- Error rates (Sentry)






