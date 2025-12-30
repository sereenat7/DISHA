"""
Logging configuration for the agentic disaster response system.
"""

import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class DisasterResponseFormatter(logging.Formatter):
    """Custom formatter for disaster response logs with enhanced context."""

    def format(self, record):
        # Add timestamp and disaster context if available
        record.timestamp = datetime.now().isoformat()

        # Add disaster_id to log record if available in extra
        if hasattr(record, 'disaster_id'):
            record.disaster_context = f"[Disaster: {record.disaster_id}]"
        else:
            record.disaster_context = ""

        # Add component context
        if hasattr(record, 'component'):
            record.component_context = f"[{record.component}]"
        else:
            record.component_context = ""

        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """
    Set up logging configuration for the disaster response system.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_console: Whether to enable console logging
    """

    # Create logs directory if logging to file
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Define log format
    log_format = (
        "%(timestamp)s - %(levelname)s - %(name)s%(disaster_context)s%(component_context)s - "
        "%(message)s"
    )

    # Configure handlers
    handlers = {}

    if enable_console:
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'disaster_response',
            'stream': sys.stdout
        }

    if log_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'disaster_response',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        }

    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'disaster_response': {
                '()': DisasterResponseFormatter,
                'format': log_format
            }
        },
        'handlers': handlers,
        'loggers': {
            'agentic_disaster_response': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            # Also capture logs from related systems
            'Backend.evacuation_system': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': list(handlers.keys())
        }
    }

    logging.config.dictConfig(config)


def get_logger(name: str, disaster_id: Optional[str] = None, component: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with optional disaster and component context.

    Args:
        name: Logger name
        disaster_id: Optional disaster ID for context
        component: Optional component name for context

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Create a custom adapter to add context
    class DisasterResponseLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get('extra', {})
            if disaster_id:
                extra['disaster_id'] = disaster_id
            if component:
                extra['component'] = component
            kwargs['extra'] = extra
            return msg, kwargs

    return DisasterResponseLoggerAdapter(logger, {})
