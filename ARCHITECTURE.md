# Production Architecture - Nepal Times News Platform

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Puter.js)                      │
│  - React/Vanilla JS Components                              │
│  - Lazy Loading, SEO-Optimized                              │
│  - Mobile Responsive                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────┴──────────────────────────────────────┐
│                    API Gateway Layer                         │
│  - Flask REST API                                           │
│  - Rate Limiting                                            │
│  - Authentication (future)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Scraper     │ │ Summarizer │ │   Image    │
│  Service     │ │  Service   │ │ Processor  │
└───────┬──────┘ └─────┬──────┘ └─────┬──────┘
        │              │              │
┌───────┴──────────────┴──────────────┴──────┐
│           PostgreSQL Database               │
│  - Articles (raw + metadata)                │
│  - Summaries (cached)                       │
│  - Images (processed)                       │
│  - Sources, Jobs, Logs                      │
└─────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────┐
│        Background Jobs (Celery/APScheduler) │
│  - Hourly scraping                          │
│  - Cleanup tasks                            │
│  - Cache warming                            │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Database Choice: PostgreSQL
- ACID compliance for data integrity
- JSONB for flexible metadata storage
- Full-text search capabilities
- Excellent for multilingual content (UTF-8 native)
- Proven scalability

### 2. Scraping Strategy
- Respect robots.txt (using urllib.robotparser)
- Rate limiting per domain
- Exponential backoff on errors
- User-Agent rotation
- Session management for cookies

### 3. Language Detection
- Use `langdetect` library (supports 55+ languages)
- Store detected language with confidence score
- Preserve original encoding (UTF-8)

### 4. Summarization
- On-demand generation (not pre-computed)
- Cache summaries in database
- Use LLM API (OpenAI/Anthropic/Gemini)
- Fallback to extractive summarization

### 5. Image Processing
- Detect watermarks using CV/ML
- Remove watermarks using inpainting
- Store processed images separately
- Generate alt text for SEO

### 6. Caching Strategy
- Redis for hot data (recent articles)
- Database for persistent cache
- CDN for images (future)

## Data Flow

1. **Scraping**: Hourly job → Fetch articles → Store raw content
2. **Deduplication**: Hash-based comparison → Merge duplicates
3. **Language Detection**: Auto-detect → Store with article
4. **User Request**: Fetch article → Check summary cache → Generate if needed
5. **Image Processing**: Detect watermark → Process → Serve

## Scalability Considerations

- Horizontal scaling: Multiple worker processes
- Database connection pooling
- Async operations for I/O-bound tasks
- Queue-based processing for heavy operations
- CDN for static assets






