"""
Production Configuration for Nepal Times News Platform
Use environment variables for sensitive data
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Database Configuration
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'nepal_times'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
    'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),
    'pool_pre_ping': True,
    'echo': os.getenv('DB_ECHO', 'False').lower() == 'true'
}

# Redis Configuration (for caching and Celery)
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'decode_responses': True
}

# Scraping Configuration
SCRAPING_CONFIG = {
    'request_timeout': int(os.getenv('SCRAPING_TIMEOUT', 30)),
    'max_retries': int(os.getenv('SCRAPING_MAX_RETRIES', 3)),
    'retry_delay': int(os.getenv('SCRAPING_RETRY_DELAY', 2)),  # seconds
    'user_agent': os.getenv('USER_AGENT', 'NepalTimesBot/1.0 (+https://nepaltimes.com/bot)'),
    'respect_robots_txt': os.getenv('RESPECT_ROBOTS_TXT', 'True').lower() == 'true',
    'rate_limit_enabled': os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true',
    'default_rate_limit_per_minute': int(os.getenv('DEFAULT_RATE_LIMIT', 10)),
    'concurrent_scrapers': int(os.getenv('CONCURRENT_SCRAPERS', 3))
}

# AI/LLM Configuration
AI_CONFIG = {
    # OpenAI
    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
    'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview'),
    'openai_temperature': float(os.getenv('OPENAI_TEMPERATURE', 0.3)),
    
    # Anthropic Claude
    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', ''),
    'anthropic_model': os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
    
    # Google Gemini
    'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
    'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-pro'),
    
    # Default provider
    'default_provider': os.getenv('AI_PROVIDER', 'openai'),  # openai, anthropic, gemini
    
    # Summary settings
    'summary_max_words': int(os.getenv('SUMMARY_MAX_WORDS', 150)),
    'summary_min_words': int(os.getenv('SUMMARY_MIN_WORDS', 80)),
    'summary_cache_ttl_days': int(os.getenv('SUMMARY_CACHE_TTL_DAYS', 30))
}

# Image Processing Configuration
IMAGE_CONFIG = {
    'storage_path': os.getenv('IMAGE_STORAGE_PATH', str(BASE_DIR / 'storage' / 'images')),
    'max_image_size_mb': int(os.getenv('MAX_IMAGE_SIZE_MB', 10)),
    'supported_formats': ['jpeg', 'jpg', 'png', 'webp'],
    'watermark_detection_enabled': os.getenv('WATERMARK_DETECTION_ENABLED', 'True').lower() == 'true',
    'watermark_removal_enabled': os.getenv('WATERMARK_REMOVAL_ENABLED', 'True').lower() == 'true',
    'image_quality': int(os.getenv('IMAGE_QUALITY', 85)),  # JPEG quality 0-100
    'max_width': int(os.getenv('IMAGE_MAX_WIDTH', 1920)),
    'max_height': int(os.getenv('IMAGE_MAX_HEIGHT', 1080))
}

# Scheduler Configuration
SCHEDULER_CONFIG = {
    'scraping_interval_hours': int(os.getenv('SCRAPING_INTERVAL_HOURS', 1)),
    'cleanup_days': int(os.getenv('CLEANUP_DAYS', 90)),  # Delete articles older than X days
    'timezone': os.getenv('TIMEZONE', 'Asia/Kathmandu')
}

# API Configuration
API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', 5000)),
    'debug': os.getenv('API_DEBUG', 'False').lower() == 'true',
    'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
    'rate_limit_per_minute': int(os.getenv('API_RATE_LIMIT', 60)),
    'max_articles_per_request': int(os.getenv('MAX_ARTICLES_PER_REQUEST', 100))
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': os.getenv('LOG_FORMAT', 'json'),  # json or text
    'file_path': os.getenv('LOG_FILE_PATH', str(BASE_DIR / 'logs' / 'app.log')),
    'max_file_size_mb': int(os.getenv('LOG_MAX_SIZE_MB', 100)),
    'backup_count': int(os.getenv('LOG_BACKUP_COUNT', 10)),
    'sentry_dsn': os.getenv('SENTRY_DSN', '')  # For error tracking
}

# Feature Flags
FEATURES = {
    'ai_summarization': os.getenv('FEATURE_AI_SUMMARIZATION', 'True').lower() == 'true',
    'image_processing': os.getenv('FEATURE_IMAGE_PROCESSING', 'True').lower() == 'true',
    'language_detection': os.getenv('FEATURE_LANGUAGE_DETECTION', 'True').lower() == 'true',
    'deduplication': os.getenv('FEATURE_DEDUPLICATION', 'True').lower() == 'true'
}

# Security
SECURITY_CONFIG = {
    'secret_key': os.getenv('SECRET_KEY', os.urandom(32).hex()),
    'jwt_secret': os.getenv('JWT_SECRET', os.urandom(32).hex()),
    'allowed_hosts': os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
}

# Create necessary directories
for path in [
    IMAGE_CONFIG['storage_path'],
    Path(LOGGING_CONFIG['file_path']).parent
]:
    Path(path).mkdir(parents=True, exist_ok=True)






