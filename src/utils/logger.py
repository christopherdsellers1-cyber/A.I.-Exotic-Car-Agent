import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logger(name: str, level: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    logger = logging.getLogger(name)

    # Get level from env or parameter
    if level is None:
        import os
        level = os.getenv('LOG_LEVEL', 'INFO')

    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


class Logger:
    """Convenience wrapper for logger setup."""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create logger."""
        if name not in cls._loggers:
            log_file = f"logs/{name}.log"
            cls._loggers[name] = setup_logger(name, log_file=log_file)
        return cls._loggers[name]


# Convenience shortcuts
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return Logger.get_logger(name)
