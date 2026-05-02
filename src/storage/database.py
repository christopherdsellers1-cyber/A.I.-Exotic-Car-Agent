from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

from src.storage.models import Base


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize database connection pool."""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'exotic_car_db')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'postgres')

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            echo=False,
            connect_args={
                'connect_timeout': 10,
                'options': '-c statement_timeout=30000'
            }
        )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session for use in context manager."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """Get a direct database session (manual close required)."""
        return self.SessionLocal()

    def close(self):
        """Close all connections."""
        self.engine.dispose()

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.engine.connect() as connection:
                connection.execute("SELECT 1")
            return True
        except Exception as e:
            return False


# Global instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get or create database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db():
    """Initialize database with tables."""
    db = get_db_manager()
    db.create_tables()
