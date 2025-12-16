import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from pytz import timezone

from core.config import settings
from database.session import async_session, engine, Base
from services.scraper import AutoRiaScraper
from services.backup import PostgresBackupService


class ScraperApplication:
    """Main application class responsible for managing the scraper and backup lifecycle.

    This class initializes the necessary components (scheduler, database connection),
    performs startup checks, and manages the main application loop.

    Attributes:
        scheduler (AsyncIOScheduler): The scheduler instance for running periodic tasks.
        stop_event (asyncio.Event): Event to signal application shutdown.
    """

    def __init__(self):
        """Initializes the application with a scheduler and a stop event.

        Sets the scheduler timezone to 'Europe/Kyiv' to ensure correct execution times
        regardless of the container's system time.
        """
        self.scheduler = AsyncIOScheduler(timezone=timezone("Europe/Kyiv"))
        self.stop_event = asyncio.Event()

    async def _init_database(self):
        """Initializes database tables.

        Checks for the existence of tables defined in SQLAlchemy models and creates
        them if they are missing using the asynchronous engine.
        """
        logger.info("🏗️ Checking database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified/created.")

    async def scheduled_job(self):
        """The main task executed by the scheduler.

        This method performs the scraping process followed by a database backup.
        It handles exceptions internally to ensure logging without crashing the scheduler.
        """
        logger.info("⏰ Scheduler triggered scraper job")

        try:
            async with async_session() as db:
                scraper = AutoRiaScraper(db)
                await scraper.run()
        except Exception as e:
            logger.error(f"Scraper job failed: {e}")

        try:
            backup_service = PostgresBackupService(settings.SYNC_DATABASE_URL)
            backup_service.create_dump()
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")

    def start_scheduler(self):
        """Configures and starts the asynchronous scheduler.

        Schedules the 'scheduled_job' to run daily at the time specified in
        the configuration settings (RUN_TIME_HOUR:RUN_TIME_MINUTE).
        """
        self.scheduler.add_job(
            self.scheduled_job,
            "cron",
            hour=settings.RUN_TIME_HOUR,
            minute=settings.RUN_TIME_MINUTE,
        )
        self.scheduler.start()
        logger.info(
            f"⏳ Scheduler started. Job scheduled for {settings.RUN_TIME_HOUR:02d}:{settings.RUN_TIME_MINUTE:02d} (Kyiv time) daily."
        )

    async def run(self):
        """The main entry point for the application.

        Orchestrates the startup sequence:
        1. Initializes the database.
        2. Starts the scheduler.
        3. Keeps the application running until a stop signal is received.
        """
        await self._init_database()
        self.start_scheduler()

        try:
            await self.stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Application stopping...")
        finally:
            self.scheduler.shutdown()
            logger.info("👋 Application shutdown complete.")


if __name__ == "__main__":
    app = ScraperApplication()
    try:
        asyncio.run(app.run())
    except (KeyboardInterrupt, SystemExit):
        pass
