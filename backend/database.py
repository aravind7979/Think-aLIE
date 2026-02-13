import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load .env only if it exists locally (for development)
if os.path.exists(".env"):
    load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Exported symbols
engine = None
SessionLocal = None
Base = declarative_base()


def init_db(raise_on_error: bool = False):
    """Initialize the SQLAlchemy engine and session factory.

    Call this at application startup. If the database is unreachable this
    function will either raise the exception (when `raise_on_error=True`)
    or log a warning and leave `engine` as None.
    """
    global engine, SessionLocal

    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set; skipping DB initialization")
        return None

    try:
        # Ensure SSL for hosted Postgres services if not provided in the URL
        connect_args = {}
        if "://" in DATABASE_URL and "sslmode" not in DATABASE_URL:
            connect_args = {"sslmode": "require"}

        logger.info("Connecting to database")
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=connect_args,
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        logger.info("Database engine created")
        return engine

    except Exception as e:
        logger.warning("Database initialization failed: %s", e)
        engine = None
        SessionLocal = None
        if raise_on_error:
            raise
        return None