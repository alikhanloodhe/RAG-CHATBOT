import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from app.core.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

postgres_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
engine = postgres_engine

async def init_db():
    """Initializes the database connection engine and registers metadata schemas.

    Tests the database connectivity, falling back or raising errors if PostgreSQL 
    cannot be reached. Then creates all database tables declared by SQLModel.
    """
    global engine
    try:
        # Run a simple query to verify postgres connection
        async with postgres_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        engine = postgres_engine
        logger.info("Database connected", extra={"backend": "postgresql"})
    except Exception as e:
        raise RuntimeError("Local PostgreSQL database is required and could not be reached") from e

    # Generate tables
    async with engine.begin() as conn:
        # Avoid import cycles by importing models inside if needed
        # But SQLModel.metadata.create_all will register all imported subclasses of SQLModel
        from app.models.models import UserDocument
        await conn.run_sync(SQLModel.metadata.create_all)

def get_engine():
    """Retrieves the active global SQLAlchemy async database engine.

    Returns:
        The active database Engine.
    """
    global engine
    return engine

async def get_session() -> AsyncSession:
    """FastAPI dependency yielding an active database session.

    Yields:
        An active SQLModel AsyncSession instance.
    """
    async_session = sessionmaker(
        get_engine(), class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
