-- Production Database Schema for Nepal Times News Platform
-- PostgreSQL 12+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Sources table: Track news sources
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    rss_url VARCHAR(500),
    robots_txt_url VARCHAR(500),
    enabled BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 10,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Articles table: Store raw scraped articles
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    
    -- Content (preserve original encoding)
    headline TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,  -- Full article text, UTF-8 encoded
    content_hash VARCHAR(64) NOT NULL,  -- SHA256 for deduplication
    
    -- Metadata
    url VARCHAR(1000) UNIQUE NOT NULL,
    language VARCHAR(10),  -- ISO 639-1 code (en, ne, hi, etc.)
    language_confidence DECIMAL(3,2),  -- 0.00 to 1.00
    
    -- Media
    original_image_url VARCHAR(1000),
    processed_image_url VARCHAR(1000),
    image_hash VARCHAR(64),
    
    -- Publication info
    published_at TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    authors TEXT[],  -- Array of author names
    category VARCHAR(100),
    tags TEXT[],
    
    -- Source metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}',
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of UUID REFERENCES articles(id),
    
    -- Indexing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Summaries table: Store AI-generated summaries (cached)
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    
    -- Summary content
    summary_text TEXT NOT NULL,
    summary_length INTEGER,  -- Word count
    language VARCHAR(10) NOT NULL,  -- Language of summary
    
    -- AI metadata
    model_used VARCHAR(100),  -- e.g., "gpt-4", "claude-3", "gemini-pro"
    prompt_version VARCHAR(20),
    generation_time_ms INTEGER,
    
    -- Cache info
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,  -- For cache invalidation
    
    UNIQUE(article_id, language, model_used)
);

-- Images table: Track processed images
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    
    -- Image data
    original_url VARCHAR(1000) NOT NULL,
    processed_url VARCHAR(1000),
    storage_path VARCHAR(500),
    
    -- Processing metadata
    has_watermark BOOLEAN DEFAULT FALSE,
    watermark_detected_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_method VARCHAR(100),
    
    -- Image properties
    width INTEGER,
    height INTEGER,
    file_size_bytes BIGINT,
    format VARCHAR(10),  -- jpeg, png, webp
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scraping jobs: Track scraping runs
CREATE TABLE scraping_jobs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    
    -- Job info
    status VARCHAR(20) NOT NULL,  -- running, completed, failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Results
    articles_found INTEGER DEFAULT 0,
    articles_new INTEGER DEFAULT 0,
    articles_updated INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    
    -- Metadata
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Deduplication log: Track duplicate detection
CREATE TABLE duplicate_groups (
    id SERIAL PRIMARY KEY,
    primary_article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    duplicate_count INTEGER DEFAULT 1,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sources TEXT[],  -- Array of source keys
    UNIQUE(primary_article_id)
);

-- Indexes for performance
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_articles_url ON articles(url);
CREATE INDEX idx_articles_content_hash ON articles(content_hash);
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_language ON articles(language);
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_scraped_at ON articles(scraped_at DESC);

-- Full-text search index (supports multiple languages)
CREATE INDEX idx_articles_content_fts ON articles USING GIN(to_tsvector('english', headline || ' ' || COALESCE(description, '')));
CREATE INDEX idx_articles_headline_trgm ON articles USING GIN(headline gin_trgm_ops);

-- Summary indexes
CREATE INDEX idx_summaries_article_id ON summaries(article_id);
CREATE INDEX idx_summaries_language ON summaries(language);
CREATE INDEX idx_summaries_expires_at ON summaries(expires_at) WHERE expires_at IS NOT NULL;

-- Image indexes
CREATE INDEX idx_images_article_id ON images(article_id);
CREATE INDEX idx_images_status ON images(status);

-- Job indexes
CREATE INDEX idx_scraping_jobs_source_id ON scraping_jobs(source_id);
CREATE INDEX idx_scraping_jobs_started_at ON scraping_jobs(started_at DESC);
CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default sources
INSERT INTO sources (key, name, base_url, rss_url, robots_txt_url) VALUES
    ('ekantipur', 'Ekantipur', 'https://ekantipur.com', 'https://ekantipur.com/rss', 'https://ekantipur.com/robots.txt'),
    ('onlinekhabar', 'Onlinekhabar', 'https://www.onlinekhabar.com', 'https://www.onlinekhabar.com/feed', 'https://www.onlinekhabar.com/robots.txt'),
    ('setopati', 'Setopati', 'https://www.setopati.com', 'https://www.setopati.com/rss', 'https://www.setopati.com/robots.txt'),
    ('cnn', 'CNN', 'https://edition.cnn.com', 'http://rss.cnn.com/rss/edition.rss', 'https://edition.cnn.com/robots.txt'),
    ('bbcnepali', 'BBC Nepali', 'https://www.bbc.com/nepali', 'https://feeds.bbci.co.uk/nepali/rss.xml', 'https://www.bbc.com/robots.txt')
ON CONFLICT (key) DO NOTHING;

-- Views for common queries
CREATE OR REPLACE VIEW recent_articles AS
SELECT 
    a.id,
    a.headline,
    a.description,
    a.url,
    a.published_at,
    a.language,
    a.category,
    s.name as source_name,
    s.key as source_key,
    a.processed_image_url as image_url,
    a.created_at
FROM articles a
LEFT JOIN sources s ON a.source_id = s.id
WHERE a.status = 'active'
ORDER BY a.published_at DESC NULLS LAST, a.scraped_at DESC;

CREATE OR REPLACE VIEW featured_articles AS
SELECT 
    a.*,
    s.name as source_name,
    COUNT(dg.id) as duplicate_count
FROM articles a
LEFT JOIN sources s ON a.source_id = s.id
LEFT JOIN duplicate_groups dg ON a.id = dg.primary_article_id
WHERE a.status = 'active' AND a.is_duplicate = FALSE
GROUP BY a.id, s.name
HAVING COUNT(dg.id) >= 2
ORDER BY duplicate_count DESC, a.published_at DESC;






