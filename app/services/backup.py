import os
import subprocess
from datetime import datetime
from loguru import logger


class PostgresBackupService:
    """Handles database backup creation.

    This service executes shell commands to generate SQL dumps of the database
    using the pg_dump utility.

    Attributes:
        db_url (str): The PostgreSQL connection URL.
        backup_dir (str): The directory path where backup files are stored.
    """

    def __init__(self, db_url: str, backup_dir: str = "dumps"):
        """Initializes the backup service.

        Args:
            db_url (str): The connection string for the PostgreSQL database.
            backup_dir (str, optional): Directory to store dumps. Defaults to "dumps".
        """
        self.db_url = db_url
        self.backup_dir = backup_dir

        os.makedirs(self.backup_dir, exist_ok=True)

    def create_dump(self) -> None:
        """Generates a new database dump using pg_dump.

        Constructs a timestamped filename and executes the pg_dump command via
        a subprocess.

        Raises:
            subprocess.CalledProcessError: If the pg_dump command fails.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"backup_{timestamp}.sql"
        filepath = os.path.join(self.backup_dir, filename)

        logger.info(f"Starting database backup: {filename}")

        command = f"pg_dump {self.db_url} > {filepath}"

        try:
            subprocess.run(command, shell=True, check=True)
            logger.info(f"Backup created successfully: {filepath}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error, backup failed: {e}")
            raise e
