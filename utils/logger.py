"""
Logging utility for retroMaid
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

console = Console()


class Logger:
    """Centralized logging system with rich console output"""

    _instance: Optional[logging.Logger] = None

    @classmethod
    def setup(cls, log_file: str = "retromaid.log", level: str = "INFO", console_output: bool = True):
        """
        Set up the logger with file and console handlers

        Args:
            log_file: Path to log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            console_output: Whether to also log to console
        """
        if cls._instance is not None:
            return cls._instance

        logger = logging.getLogger("retroMaid")
        logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        logger.handlers.clear()

        # File handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler with rich
        if console_output:
            console_handler = RichHandler(
                console=console,
                show_time=False,
                show_path=False,
                markup=True,
            )
            console_handler.setLevel(getattr(logging, level.upper()))
            logger.addHandler(console_handler)

        cls._instance = logger
        return logger

    @classmethod
    def get(cls) -> logging.Logger:
        """Get the logger instance"""
        if cls._instance is None:
            return cls.setup()
        return cls._instance


def get_logger() -> logging.Logger:
    """Convenience function to get logger"""
    return Logger.get()
