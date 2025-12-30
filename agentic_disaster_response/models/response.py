"""
Disaster response and result models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from .alert_priority import AlertPriority
from .context import StructuredContext


class DispatchStatus(Enum):
    """Status of alert dispatch operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RETRYING = "retrying"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DispatchResult:
    """Result of alert dispatch operation."""
    dispatch_id: str
    mcp_tool_name: str
    status: DispatchStatus
    timestamp: datetime
    recipients_count: int
    successful_deliveries: int
    failed_deliveries: int
    error_message: Optional[str] = None
    retry_count: int = 0
    execution_time_seconds: Optional[float] = None


@dataclass
class ErrorRecord:
    """Record of errors that occurred during processing."""
    error_id: str
    timestamp: datetime
    component: str  # Which component generated the error
    severity: ErrorSeverity
    error_type: str
    error_message: str
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_action_taken: Optional[str] = None
    resolved: bool = False


@dataclass
class DisasterResponse:
    """Complete response record for a disaster event."""
    disaster_id: str
    processing_status: str  # From ProcessingStatus enum
    context: Optional[StructuredContext] = None
    priority: Optional[AlertPriority] = None
    dispatch_results: List[DispatchResult] = field(default_factory=list)
    completion_time: Optional[datetime] = None
    errors: List[ErrorRecord] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    total_processing_time_seconds: Optional[float] = None

    def add_error(self, component: str, severity: ErrorSeverity, error_type: str,
                  error_message: str, context: Optional[Dict[str, Any]] = None,
                  recovery_action: Optional[str] = None) -> ErrorRecord:
        """Add an error record to this response."""
        import uuid

        error = ErrorRecord(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            component=component,
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            context=context or {},
            recovery_action_taken=recovery_action
        )
        self.errors.append(error)
        return error

    def mark_completed(self):
        """Mark the response as completed and calculate processing time."""
        self.completion_time = datetime.now()
        if self.start_time:
            self.total_processing_time_seconds = (
                self.completion_time - self.start_time
            ).total_seconds()

    @property
    def has_critical_errors(self) -> bool:
        """Check if response has any critical errors."""
        return any(error.severity == ErrorSeverity.CRITICAL for error in self.errors)

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate of dispatch operations."""
        if not self.dispatch_results:
            return 0.0

        total_recipients = sum(
            result.recipients_count for result in self.dispatch_results)
        if total_recipients == 0:
            return 0.0

        successful_deliveries = sum(
            result.successful_deliveries for result in self.dispatch_results)
        return successful_deliveries / total_recipients
