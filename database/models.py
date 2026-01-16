"""
SQLAlchemy ORM Models for Nepal Times News Platform
Production-grade models with proper relationships and constraints
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, ARRAY, JSON, DECIMAL, BigInteger, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY as PG_ARRAY
from datetime import datetime
import uuid

Base = declarative_base()


class Source(Base):
    """News source (portal) model"""
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    base_url = Column(String(500), nullable=False)
    rss_url = Column(String(500))
    robots_txt_url = Column(String(500))
    enabled = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=10)
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", back_populates="source", lazy="dynamic")
    scraping_jobs = relationship("ScrapingJob", back_populates="source", lazy="dynamic")
    
    def __repr__(self):
        return f"<Source(key='{self.key}', name='{self.name}')>"


class Article(Base):
    """Article model - stores scraped news articles"""
    __tablename__ = 'articles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(Integer, ForeignKey('sources.id', ondelete='SET NULL'), index=True)
    
    # Content (preserve original encoding)
    headline = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256
    
    # Metadata
    url = Column(String(1000), unique=True, nullable=False, index=True)
    language = Column(String(10), index=True)  # ISO 639-1
    language_confidence = Column(DECIMAL(3, 2))
    
    # Media
    original_image_url = Column(String(1000))
    processed_image_url = Column(String(1000))
    image_hash = Column(String(64))
    
    # Publication info
    published_at = Column(DateTime(timezone=True), index=True)
    scraped_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    authors = Column(PG_ARRAY(Text))
    category = Column(String(100))
    tags = Column(PG_ARRAY(Text))
    
    # Source metadata
    metadata = Column(JSONB, default={})
    
    # Status
    status = Column(String(20), default='active', index=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey('articles.id'))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source = relationship("Source", back_populates="articles")
    summaries = relationship("Summary", back_populates="article", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="article", cascade="all, delete-orphan")
    duplicate_group = relationship("DuplicateGroup", back_populates="primary_article", uselist=False)
    
    # Indexes for full-text search (created separately)
    __table_args__ = (
        Index('idx_articles_content_fts', 'headline', 'description', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Article(id={self.id}, headline='{self.headline[:50]}...')>"


class Summary(Base):
    """AI-generated summaries cache"""
    __tablename__ = 'summaries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Summary content
    summary_text = Column(Text, nullable=False)
    summary_length = Column(Integer)  # Word count
    language = Column(String(10), nullable=False, index=True)
    
    # AI metadata
    model_used = Column(String(100))
    prompt_version = Column(String(20))
    generation_time_ms = Column(Integer)
    
    # Cache info
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), index=True)
    
    # Relationships
    article = relationship("Article", back_populates="summaries")
    
    __table_args__ = (
        Index('idx_summaries_article_language_model', 'article_id', 'language', 'model_used', unique=True),
    )
    
    def __repr__(self):
        return f"<Summary(article_id={self.article_id}, language='{self.language}')>"


class Image(Base):
    """Processed images"""
    __tablename__ = 'images'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Image data
    original_url = Column(String(1000), nullable=False)
    processed_url = Column(String(1000))
    storage_path = Column(String(500))
    
    # Processing metadata
    has_watermark = Column(Boolean, default=False)
    watermark_detected_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    processing_method = Column(String(100))
    
    # Image properties
    width = Column(Integer)
    height = Column(Integer)
    file_size_bytes = Column(BigInteger)
    format = Column(String(10))
    
    # Status
    status = Column(String(20), default='pending', index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    article = relationship("Article", back_populates="images")
    
    def __repr__(self):
        return f"<Image(id={self.id}, status='{self.status}')>"


class ScrapingJob(Base):
    """Track scraping runs"""
    __tablename__ = 'scraping_jobs'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id', ondelete='SET NULL'), index=True)
    
    # Job info
    status = Column(String(20), nullable=False, index=True)  # running, completed, failed
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    articles_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    # Metadata
    error_message = Column(Text)
    metadata = Column(JSONB, default={})
    
    # Relationships
    source = relationship("Source", back_populates="scraping_jobs")
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, status='{self.status}')>"


class DuplicateGroup(Base):
    """Track duplicate article groups"""
    __tablename__ = 'duplicate_groups'
    
    id = Column(Integer, primary_key=True)
    primary_article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), unique=True, nullable=False)
    duplicate_count = Column(Integer, default=1)
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sources = Column(PG_ARRAY(Text))
    
    # Relationships
    primary_article = relationship("Article", back_populates="duplicate_group")
    
    def __repr__(self):
        return f"<DuplicateGroup(primary_article_id={self.primary_article_id}, count={self.duplicate_count})>"






