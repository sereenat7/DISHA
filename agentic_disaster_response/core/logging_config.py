"""
Logging configuration for the agentic disaster response system.
"""

import logging
import logging.config
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


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

        # Add workflow step context
        if hasattr(record, 'workflow_step'):
            record.workflow_context = f"[Step: {record.workflow_step}]"
        else:
            record.workflow_context = ""

        # Add action context for detailed workflow logging
        if hasattr(record, 'action'):
            record.action_context = f"[Action: {record.action}]"
        else:
            record.action_context = ""

        # Add recovery context for error handling
        if hasattr(record, 'recovery_action'):
            record.recovery_context = f"[Recovery: {record.recovery_action}]"
        else:
            record.recovery_context = ""

        return super().format(record)


class StructuredLogFormatter(logging.Formatter):
    """Structured JSON formatter for machine-readable logs."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add disaster context
        if hasattr(record, 'disaster_id'):
            log_entry['disaster_id'] = record.disaster_id

        # Add component context
        if hasattr(record, 'component'):
            log_entry['component'] = record.component

        # Add workflow step
        if hasattr(record, 'workflow_step'):
            log_entry['workflow_step'] = record.workflow_step

        # Add action details
        if hasattr(record, 'action'):
            log_entry['action'] = record.action

        # Add recovery information
        if hasattr(record, 'recovery_action'):
            log_entry['recovery_action'] = record.recovery_action

        # Add error context
        if hasattr(record, 'error_context'):
            log_entry['error_context'] = record.error_context

        # Add dispatch information
        if hasattr(record, 'dispatch_info'):
            log_entry['dispatch_info'] = record.dispatch_info

        # Add performance metrics
        if hasattr(record, 'performance_metrics'):
            log_entry['performance_metrics'] = record.performance_metrics

        # Add exception information
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_structured_logging: bool = False
) -> None:
    """
    Set up logging configuration for the disaster response system.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_console: Whether to enable console logging
        enable_structured_logging: Whether to enable structured JSON logging
    """

    # Create logs directory if logging to file
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Define log formats
    human_readable_format = (
        "%(timestamp)s - %(levelname)s - %(name)s%(disaster_context)s%(component_context)s"
        "%(workflow_context)s%(action_context)s%(recovery_context)s - %(message)s"
    )

    # Configure handlers
    handlers = {}

    if enable_console:
        formatter_name = 'structured' if enable_structured_logging else 'disaster_response'
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': formatter_name,
            'stream': sys.stdout
        }

    if log_file:
        # Always use structured logging for file output for better parsing
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'structured',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        }

        # Also create a human-readable file handler
        human_readable_file = str(log_path).replace('.log', '_readable.log')
        handlers['file_readable'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'disaster_response',
            'filename': human_readable_file,
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
                'format': human_readable_format
            },
            'structured': {
                '()': StructuredLogFormatter
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

        def log_workflow_step(self, level: int, msg: str, workflow_step: str,
                              action: Optional[str] = None, **kwargs):
            """Log a workflow step with structured context."""
            extra = kwargs.get('extra', {})
            extra['workflow_step'] = workflow_step
            if action:
                extra['action'] = action
            kwargs['extra'] = extra
            self.log(level, msg, **kwargs)

        def log_error_with_recovery(self, msg: str, error_context: Dict[str, Any],
                                    recovery_action: Optional[str] = None, **kwargs):
            """Log an error with recovery context."""
            extra = kwargs.get('extra', {})
            extra['error_context'] = error_context
            if recovery_action:
                extra['recovery_action'] = recovery_action
            kwargs['extra'] = extra
            self.error(msg, **kwargs)

        def log_dispatch_result(self, msg: str, dispatch_info: Dict[str, Any], **kwargs):
            """Log alert dispatch results with delivery status."""
            extra = kwargs.get('extra', {})
            extra['dispatch_info'] = dispatch_info
            kwargs['extra'] = extra
            self.info(msg, **kwargs)

        def log_performance_metrics(self, msg: str, metrics: Dict[str, Any], **kwargs):
            """Log performance metrics."""
            extra = kwargs.get('extra', {})
            extra['performance_metrics'] = metrics
            kwargs['extra'] = extra
            self.info(msg, **kwargs)

    return DisasterResponseLoggerAdapter(logger, {})
