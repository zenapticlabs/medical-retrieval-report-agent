from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import time
import logging
from app.core.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

def create_database_engine():
    """Create database engine with retry mechanism"""
    database_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    
    # Add connection pool settings for better reliability
    engine = create_engine(
        database_url,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections every hour
        pool_size=10,        # Connection pool size
        max_overflow=20,     # Maximum overflow connections
        echo=False           # Set to True for SQL debugging
    )
    
    return engine

# Create database engine
engine = create_database_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def wait_for_database(max_retries=30, retry_interval=2):
    """Wait for database to be ready"""
    logger.info("Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
        except OperationalError as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                logger.error("Failed to connect to database after all retries")
                return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            return False

# Create all tables
def init_db():
    """Initialize database tables"""
    try:
        if wait_for_database():
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        else:
            logger.error("Cannot initialize database - connection failed")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 