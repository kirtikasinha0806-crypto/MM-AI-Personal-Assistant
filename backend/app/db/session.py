import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for declarative models
Base = declarative_base()

SQLITE_FALLBACK_URL = "sqlite:///./local_assistant.db"
_using_fallback = False


def _try_create_postgres_engine():
    """Attempts to create a PostgreSQL engine. Returns None on failure."""
    try:
        eng = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={}
        )
        # Quick connection test
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL connection successful.")
        return eng
    except Exception as e:
        logger.warning(f"PostgreSQL unavailable ({e}). Falling back to SQLite for local development.")
        return None


def _create_sqlite_engine():
    """Creates a SQLite engine for local development fallback."""
    eng = create_engine(
        SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    logger.info(f"Using SQLite fallback database: {SQLITE_FALLBACK_URL}")
    return eng


# Try PostgreSQL first, fall back to SQLite
if "postgresql" in settings.DATABASE_URL:
    engine = _try_create_postgres_engine()
    if engine is None:
        _using_fallback = True
        engine = _create_sqlite_engine()
else:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database tables and enables pgvector extension if using PostgreSQL."""
    global engine, SessionLocal, _using_fallback
    try:
        with engine.connect() as connection:
            if "postgresql" in str(engine.url):
                logger.info("Enabling pgvector extension...")
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                connection.commit()
            logger.info("Creating all database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info(f"Database ready ({'PostgreSQL+pgvector' if not _using_fallback else 'SQLite fallback'}).")
            return True
    except Exception as e:
        logger.error(f"Database init error: {e}")
        if not _using_fallback:
            logger.warning("Retrying with SQLite fallback...")
            _using_fallback = True
            engine = _create_sqlite_engine()
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("SQLite fallback database initialized successfully.")
                return True
            except Exception as e2:
                logger.error(f"SQLite fallback also failed: {e2}")
        return False


def is_using_fallback() -> bool:
    return _using_fallback

