"""
Database package for Nepal Times News Platform
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import config_prod

# Create database engine with connection pooling
def create_db_engine():
    """Create SQLAlchemy engine with production settings"""
    db_url = (
        f"postgresql://{config_prod.DATABASE_CONFIG['user']}:"
        f"{config_prod.DATABASE_CONFIG['password']}@"
        f"{config_prod.DATABASE_CONFIG['host']}:"
        f"{config_prod.DATABASE_CONFIG['port']}/"
        f"{config_prod.DATABASE_CONFIG['database']}"
    )
    
    engine = create_engine(
        db_url,
        pool_size=config_prod.DATABASE_CONFIG['pool_size'],
        max_overflow=config_prod.DATABASE_CONFIG['max_overflow'],
        pool_pre_ping=config_prod.DATABASE_CONFIG['pool_pre_ping'],
        echo=config_prod.DATABASE_CONFIG['echo'],
        connect_args={
            "options": "-c timezone=utc"
        }
    )
    
    return engine


# Create engine and session factory
engine = create_db_engine()
SessionLocal = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Ensures proper cleanup and rollback on errors
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database - create all tables"""
    from database.models import Base
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (use with caution!)"""
    from database.models import Base
    Base.metadata.drop_all(bind=engine)






