# Nepal Times - Production News Platform

## Overview

Production-grade news aggregation platform with:
- ✅ Database architecture (PostgreSQL)
- ✅ Robots.txt compliance
- ✅ Language detection (55+ languages)
- ✅ UTF-8 encoding safety (Devanagari support)
- ✅ Rate limiting
- ✅ Configuration management
- 🔲 Scraping service (architecture ready)
- 🔲 AI summarization (architecture ready)
- 🔲 Image processing (architecture ready)
- 🔲 Production API (architecture ready)

## What's Built

### 1. Database Layer
- Complete PostgreSQL schema
- SQLAlchemy ORM models
- Proper indexes and relationships
- Multilingual support
- Deduplication tracking

### 2. Configuration
- Environment-based configuration
- Feature flags
- Security settings
- Database connection pooling

### 3. Utilities
- **Robots Parser**: Thread-safe, cached robots.txt parser
- **Rate Limiter**: Per-domain rate limiting
- **Language Detector**: Multi-language detection with confidence
- **Encoding Handler**: UTF-8 safety, preserves all Unicode scripts

## Quick Start

### Setup

```bash
# 1. Install PostgreSQL and Redis
sudo apt-get install postgresql redis-server

# 2. Create database
createdb nepal_times
psql nepal_times < database/schema.sql

# 3. Install Python dependencies
pip install -r requirements-prod.txt

# 4. Configure
cp .env.example .env
# Edit .env with your settings

# 5. Initialize (if needed)
python -c "from database import init_db; init_db()"
```

### Run (Development)

```bash
# Activate virtual environment
source venv/bin/activate

# Run API (development)
python app.py

# Or with Gunicorn (production)
gunicorn app:app --workers 4 --bind 0.0.0.0:5000
```

## Architecture

See `ARCHITECTURE.md` for detailed architecture documentation.

## Implementation Status

See `PRODUCTION_ROADMAP.md` for implementation roadmap and next steps.

## Key Features

### ✅ Implemented
- Database schema and models
- Configuration system
- Robots.txt parser
- Rate limiting
- Language detection
- Encoding handling

### 🚧 In Progress / Next Steps
- Production scraper
- Summarization service
- Image processing
- Production API
- Scheduler
- Logging system
- Frontend optimizations

## Configuration

All configuration is in `config_prod.py` and uses environment variables.

Key settings:
- Database connection
- Redis configuration
- AI/LLM API keys
- Scraping settings
- Image processing
- Logging

## Database Schema

See `database/schema.sql` for complete schema.

Main tables:
- `sources` - News sources
- `articles` - Scraped articles
- `summaries` - AI-generated summaries (cached)
- `images` - Processed images
- `scraping_jobs` - Job tracking
- `duplicate_groups` - Deduplication

## API Design

Planned endpoints:
- `GET /api/articles` - List articles (paginated, filtered)
- `GET /api/articles/{id}` - Get article with summary
- `GET /api/sources` - List sources
- `GET /api/health` - Health check
- `GET /api/metrics` - System metrics

## Deployment

See `DEPLOYMENT_GUIDE.md` for production deployment instructions.

## Development

### Code Structure
```
news/
├── database/          # Database models and schema
├── scraper/          # Scraping services
├── services/         # Business logic (summarizer, image processor)
├── utils/            # Utilities (robots, language, encoding)
├── api/              # API endpoints
├── scheduler/        # Background jobs
├── config_prod.py    # Configuration
└── app.py            # Application entry point
```

### Adding New Features

1. Database changes: Update `database/schema.sql` and models
2. Configuration: Add to `config_prod.py`
3. Utilities: Add to `utils/`
4. Services: Add to `services/`
5. API: Add endpoints to `api/`

## License

[Your License Here]

## Support

[Your Support Information Here]






