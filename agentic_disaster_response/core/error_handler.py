"""
Error handling and recovery mechanisms for the disaster response system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass

from .exceptions import DisasterResponseError
from ..models.response import ErrorRecord, ErrorSeverity


class ErrorRecoveryStrategy(Enum):
    """Strategies for error recovery."""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ESCALATE = "escalate"
    IGNORE = "ignore"


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_backoff: bool = True
    jitter: bool = True


class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function."""
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise DisasterResponseError(
                        f"Circuit breaker is OPEN for {func.__name__}",
                        component="CircuitBreaker"
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.last_failure_time is None:
            return True
        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() > self.recovery_timeout

    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorHandler:
    """Central error handling and recovery system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_strategies: Dict[Type[Exception],
                                    ErrorRecoveryStrategy] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}

        # Set up default error strategies
        self._setup_default_strategies()

    def _setup_default_strategies(self):
        """Set up default error recovery strategies."""
        from .exceptions import (
            ContextBuildingError,
            PriorityAnalysisError,
            AlertDispatchError,
            MCPToolError,
            DataValidationError,
            FastAPIIntegrationError
        )

        self.error_strategies.update({
            ContextBuildingError: ErrorRecoveryStrategy.GRACEFUL_DEGRADATION,
            PriorityAnalysisError: ErrorRecoveryStrategy.FALLBACK,
            AlertDispatchError: ErrorRecoveryStrategy.RETRY,
            MCPToolError: ErrorRecoveryStrategy.FALLBACK,
            DataValidationError: ErrorRecoveryStrategy.ESCALATE,
            FastAPIIntegrationError: ErrorRecoveryStrategy.RETRY,
            ConnectionError: ErrorRecoveryStrategy.RETRY,
            TimeoutError: ErrorRecoveryStrategy.RETRY,
        })

    def register_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ) -> CircuitBreaker:
        """Register a circuit breaker for a service."""
        circuit_breaker = CircuitBreaker(failure_threshold, recovery_timeout)
        self.circuit_breakers[service_name] = circuit_breaker
        return circuit_breaker

    def get_circuit_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a service."""
        return self.circuit_breakers.get(service_name)

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        recovery_function: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle an error with appropriate recovery strategy.

        Args:
            error: The exception that occurred
            context: Context information about the error
            recovery_function: Optional function to call for recovery

        Returns:
            Dictionary with recovery result and metadata
        """
        error_type = type(error)
        strategy = self.error_strategies.get(
            error_type, ErrorRecoveryStrategy.ESCALATE)

        # Log the error
        self.logger.error(
            f"Error occurred: {error}",
            extra={
                'disaster_id': context.get('disaster_id'),
                'component': context.get('component'),
                'error_type': error_type.__name__,
                'strategy': strategy.value
            }
        )

        # Apply recovery strategy
        if strategy == ErrorRecoveryStrategy.RETRY:
            return await self._retry_operation(error, context, recovery_function)
        elif strategy == ErrorRecoveryStrategy.FALLBACK:
            return await self._apply_fallback(error, context, recovery_function)
        elif strategy == ErrorRecoveryStrategy.GRACEFUL_DEGRADATION:
            return await self._graceful_degradation(error, context)
        elif strategy == ErrorRecoveryStrategy.ESCALATE:
            return await self._escalate_error(error, context)
        else:  # IGNORE
            return {"status": "ignored", "error": str(error)}

    async def _retry_operation(
        self,
        error: Exception,
        context: Dict[str, Any],
        recovery_function: Optional[Callable]
    ) -> Dict[str, Any]:
        """Implement retry logic with exponential backoff."""
        if not recovery_function:
            return {"status": "failed", "reason": "No recovery function provided"}

        operation_name = context.get('operation', 'unknown')
        retry_config = self.retry_configs.get(operation_name, RetryConfig())

        for attempt in range(retry_config.max_attempts):
            if attempt > 0:
                delay = min(
                    retry_config.base_delay * (2 ** (attempt - 1)),
                    retry_config.max_delay
                )
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)

                self.logger.info(
                    f"Retrying operation {operation_name}, attempt {attempt + 1}/{retry_config.max_attempts}, "
                    f"delay: {delay:.2f}s"
                )
                await asyncio.sleep(delay)

            try:
                result = await recovery_function()
                self.logger.info(
                    f"Operation {operation_name} succeeded on attempt {attempt + 1}")
                return {"status": "recovered", "attempt": attempt + 1, "result": result}
            except Exception as retry_error:
                if attempt == retry_config.max_attempts - 1:
                    self.logger.error(
                        f"Operation {operation_name} failed after {retry_config.max_attempts} attempts")
                    return {"status": "failed", "final_error": str(retry_error)}
                continue

        return {"status": "failed", "reason": "Max retries exceeded"}

    async def _apply_fallback(
        self,
        error: Exception,
        context: Dict[str, Any],
        recovery_function: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Apply fallback mechanism."""
        fallback_options = context.get('fallback_options', [])

        for fallback in fallback_options:
            try:
                self.logger.info(f"Attempting fallback: {fallback}")
                if callable(fallback):
                    result = await fallback()
                    return {"status": "fallback_success", "fallback": str(fallback), "result": result}
                else:
                    return {"status": "fallback_success", "fallback": fallback}
            except Exception as fallback_error:
                self.logger.warning(
                    f"Fallback {fallback} failed: {fallback_error}")
                continue

        return {"status": "fallback_failed", "reason": "All fallback options exhausted"}

    async def _graceful_degradation(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implement graceful degradation."""
        degraded_functionality = context.get('degraded_functionality', {})

        self.logger.warning(
            f"Entering graceful degradation mode due to: {error}",
            extra={'component': context.get('component')}
        )

        return {
            "status": "degraded",
            "available_functionality": degraded_functionality,
            "error": str(error)
        }

    async def _escalate_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Escalate error to higher level handling."""
        self.logger.critical(
            f"Escalating error: {error}",
            extra={
                'disaster_id': context.get('disaster_id'),
                'component': context.get('component')
            }
        )

        # In a real system, this would trigger alerts to administrators
        return {"status": "escalated", "error": str(error), "requires_intervention": True}

    def create_error_record(
        self,
        error: Exception,
        component: str,
        disaster_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[str] = None
    ) -> ErrorRecord:
        """Create an error record for tracking."""
        import uuid

        # Determine severity based on error type
        severity = ErrorSeverity.MEDIUM
        if isinstance(error, (ConnectionError, TimeoutError)):
            severity = ErrorSeverity.HIGH
        elif isinstance(error, DisasterResponseError):
            severity = ErrorSeverity.HIGH
        elif "critical" in str(error).lower():
            severity = ErrorSeverity.CRITICAL

        return ErrorRecord(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            component=component,
            severity=severity,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            recovery_action_taken=recovery_action
        )
