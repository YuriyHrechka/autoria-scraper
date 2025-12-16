from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


# Create the asynchronous engine using the URL from settings
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Create a session factory for creating AsyncSession instances
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models.

    All database models should inherit from this class to be correctly
    registered and mapped to the database tables.
    """
    pass
