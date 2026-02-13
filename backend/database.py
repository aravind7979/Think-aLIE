import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load .env only if it exists locally (for development)
if os.path.exists(".env"):
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Don't crash at import time - let startup event handle it
engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    print(f"✅ Connecting to database: {DATABASE_URL[:50]}...")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
else:
    print("⚠️  WARNING: DATABASE_URL not set yet (will be checked on startup)")