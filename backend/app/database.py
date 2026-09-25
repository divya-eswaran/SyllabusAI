import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)


def _create_engine():
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})

    try:
        # Test connection with 3-second timeout
        eng = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with eng.connect() as conn:
            pass
        logger.info(f"Connected to PostgreSQL database at {db_url}")
        return eng
    except Exception as e:
        logger.warning(
            f"PostgreSQL connection failed ({e}). Falling back to local SQLite database (sqlite:///./syllabusai.db)."
        )
        return create_engine("sqlite:///./syllabusai.db", connect_args={"check_same_thread": False})


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

