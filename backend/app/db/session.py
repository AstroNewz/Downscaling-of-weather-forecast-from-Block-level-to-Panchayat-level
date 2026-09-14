"""
SQLAlchemy database engine and session factory with PostGIS support.
"""
from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging import logger

# Engine with connection pool configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Keep SQL echo false for clean logging in development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session per request.
    Ensures safe commit/rollback and automatic closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        db.rollback()
        logger.error(f"Database session error: {exc}", exc_info=True)
        raise
    finally:
        db.close()


def check_database_health() -> Tuple[bool, str]:
    """
    Validates live database connectivity and checks for PostGIS extension.
    Returns (is_healthy, detail_message).
    """
    try:
        with engine.connect() as conn:
            # Check basic query execution
            conn.execute(text("SELECT 1;"))
            
            # Check if PostGIS extension is installed
            result = conn.execute(text("SELECT PostGIS_Version();")).scalar()
            if result:
                return True, f"Connected to PostgreSQL with PostGIS version {result}"
            return True, "Connected to PostgreSQL (PostGIS extension not enabled)"
    except SQLAlchemyError as err:
        logger.warning(f"Database health check failed: {err}")
        return False, f"Database connection unavailable: {str(err.__cause__ or err)}"
    except Exception as exc:
        logger.warning(f"Database unexpected health error: {exc}")
        return False, f"Database connection error: {str(exc)}"


def init_postgis_extension() -> bool:
    """
    Attempts to enable the PostGIS extension in the connected database.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            logger.info("PostGIS extension initialized successfully.")
            return True
    except Exception as exc:
        logger.warning(f"Could not auto-initialize PostGIS extension: {exc}")
        return False
