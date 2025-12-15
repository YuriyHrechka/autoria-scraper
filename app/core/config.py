from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    """Application configuration settings.

    Inherits from `BaseSettings` to automatically load configuration parameters
    from environment variables or a `.env` file. It provides separate
    properties for asynchronous and synchronous database connections.

    Attributes:
        POSTGRES_USER (str): The username for the PostgreSQL database.
        POSTGRES_PASSWORD (str): The password for the PostgreSQL database.
        POSTGRES_HOST (str): The host address of the database server (e.g., 'localhost').
        POSTGRES_PORT (int): The port number the database is listening on.
        POSTGRES_DB (str): The specific database name to connect to.
        START_URL (str): The initial URL used as an entry point.
        RUN_TIME_HOUR (int): The hour (0-23) when the scheduled task should run. Defaults to 12.
        RUN_TIME_MINUTE (int): The minute (0-59) when the scheduled task should run. Defaults to 0.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    START_URL: str

    RUN_TIME_HOUR: int = 12
    RUN_TIME_MINUTE: int = 0

    @computed_field
    def DATABASE_URL(self) -> str:
        """Constructs the asynchronous database connection URL.

        Uses the `asyncpg` driver for asynchronous database operations.

        Returns:
            str: A SQLAlchemy-compatible connection string in the format:
            `postgresql+asyncpg://user:password@host:port/dbname`.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    def SYNC_DATABASE_URL(self) -> str:
        """Constructs the synchronous database connection URL.

        Uses the standard driver for synchronous database operations.

        Returns:
            str: A SQLAlchemy-compatible connection string in the format:
            `postgresql://user:password@host:port/dbname`.
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
