from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Create the asynchronous engine using the URL from settings
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Create a session factory for creating AsyncSession instances
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False, 
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models.
    
    All database models should inherit from this class to be correctly
    registered and mapped to the database tables.
    """
    pass


async def get_db_session() -> AsyncSession:
    """Dependency for getting an asynchronous database session.

    This function is intended to be used as a FastAPI dependency. It creates
    a new `AsyncSession` for each request and ensures it is closed after 
    the request is processed.

    Yields:
        AsyncSession: An active asynchronous database session context.
    """
    async with AsyncSessionLocal() as session:
        yield session