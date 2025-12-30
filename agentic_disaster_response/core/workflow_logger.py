"""
Comprehensive workflow logging for disaster response operations.

This module provides structured logging for all workflow steps, error handling,
and alert dispatch operations as required by Requirements 7.1, 7.2, and 7.3.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from .logging_config import get_logger


class WorkflowStep(Enum):
    """Enumeration of workflow steps for structured logging."""
    INITIALIZATION = "initialization"
    DATA_RETRIEVAL = "data_retrieval"
    DATA_VALIDATION = "data_validation"
    CONTEXT_BUILDING = "context_building"
    CONTEXT_VALIDATION = "context_validation"
    PRIORITY_ANALYSIS = "priority_analysis"
    ALERT_DISPATCH = "alert_dispatch"
    ERROR_RECOVERY = "error_recovery"
    COMPLETION = "completion"


class ActionType(Enum):
    """Enumeration of action types for detailed logging."""
    START = "start"
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    FALLBACK = "fallback"
    RECOVERY = "recovery"


@dataclass
class WorkflowLogEntry:
    """Structured log entry for workflow operations."""
    disaster_id: str
    workflow_step: WorkflowStep
    action_type: ActionType
    timestamp: datetime
    component: str
    message: str
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    recovery_info: Optional[Dict[str, Any]] = None


@dataclass
class ErrorLogEntry:
    """Structured log entry for error handling."""
    disaster_id: str
    component: str
    error_type: str
    error_message: str
    timestamp: datetime
    context: Dict[str, Any]
    recovery_action: Optional[str] = None
    recovery_success: Optional[bool] = None
    stack_trace: Optional[str] = None


@dataclass
class DispatchLogEntry:
    """Structured log entry for alert dispatch operations."""
    disaster_id: str
    dispatch_id: str
    mcp_tool_name: str
    timestamp: datetime
    status: str
    recipients_count: int
    successful_deliveries: int
    failed_deliveries: int
    delivery_channels: List[str]
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class WorkflowLogger:
    """
    Comprehensive workflow logger for disaster response operations.

    Provides structured logging for all workflow steps, error handling,
    and alert dispatch operations with detailed context and metrics.
    """

    def __init__(self, disaster_id: str, component: str):
        """
        Initialize workflow logger for a specific disaster and component.

        Args:
            disaster_id: Unique identifier for the disaster
            component: Name of the component performing the workflow
        """
        self.disaster_id = disaster_id
        self.component = component
        self.logger = get_logger(
            f"agentic_disaster_response.workflow.{component}",
            disaster_id=disaster_id,
            component=component
        )
        self.workflow_start_time = datetime.now()
        self.step_start_times: Dict[WorkflowStep, datetime] = {}

    def log_workflow_start(self, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log the start of a workflow for a disaster.

        Args:
            details: Optional additional details about the workflow
        """
        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=WorkflowStep.INITIALIZATION,
            action_type=ActionType.START,
            timestamp=self.workflow_start_time,
            component=self.component,
            message=f"Starting disaster response workflow for {self.disaster_id}",
            details=details or {}
        )

        self.logger.log_workflow_step(
            logging.INFO,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_step_start(self, step: WorkflowStep, action_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log the start of a workflow step.

        Args:
            step: The workflow step being started
            action_details: Optional details about the action
        """
        start_time = datetime.now()
        self.step_start_times[step] = start_time

        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=step,
            action_type=ActionType.START,
            timestamp=start_time,
            component=self.component,
            message=f"Starting {step.value} for disaster {self.disaster_id}",
            details=action_details or {}
        )

        self.logger.log_workflow_step(
            logging.INFO,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_step_progress(self, step: WorkflowStep, progress_message: str,
                          progress_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log progress within a workflow step.

        Args:
            step: The workflow step in progress
            progress_message: Description of the progress
            progress_details: Optional details about the progress
        """
        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=step,
            action_type=ActionType.PROGRESS,
            timestamp=datetime.now(),
            component=self.component,
            message=progress_message,
            details=progress_details or {}
        )

        self.logger.log_workflow_step(
            logging.INFO,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_step_success(self, step: WorkflowStep, success_message: str,
                         result_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log successful completion of a workflow step.

        Args:
            step: The workflow step that completed successfully
            success_message: Description of the success
            result_details: Optional details about the results
        """
        end_time = datetime.now()
        duration_ms = None

        if step in self.step_start_times:
            duration_ms = (
                end_time - self.step_start_times[step]).total_seconds() * 1000

        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=step,
            action_type=ActionType.SUCCESS,
            timestamp=end_time,
            component=self.component,
            message=success_message,
            duration_ms=duration_ms,
            details=result_details or {}
        )

        self.logger.log_workflow_step(
            logging.INFO,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_step_failure(self, step: WorkflowStep, error: Exception,
                         error_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log failure of a workflow step.

        Args:
            step: The workflow step that failed
            error: The exception that caused the failure
            error_context: Optional context about the error
        """
        end_time = datetime.now()
        duration_ms = None

        if step in self.step_start_times:
            duration_ms = (
                end_time - self.step_start_times[step]).total_seconds() * 1000

        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_context': error_context or {}
        }

        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=step,
            action_type=ActionType.FAILURE,
            timestamp=end_time,
            component=self.component,
            message=f"Step {step.value} failed for disaster {self.disaster_id}: {str(error)}",
            duration_ms=duration_ms,
            error_info=error_info
        )

        self.logger.log_workflow_step(
            logging.ERROR,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_error_with_recovery(self, error: Exception, error_context: Dict[str, Any],
                                recovery_action: Optional[str] = None,
                                recovery_success: Optional[bool] = None) -> None:
        """
        Log an error with recovery context as required by Requirement 7.2.

        Args:
            error: The exception that occurred
            error_context: Context information about the error
            recovery_action: Description of recovery action taken
            recovery_success: Whether recovery was successful
        """
        import traceback

        error_entry = ErrorLogEntry(
            disaster_id=self.disaster_id,
            component=self.component,
            error_type=type(error).__name__,
            error_message=str(error),
            timestamp=datetime.now(),
            context=error_context,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            stack_trace=traceback.format_exc()
        )

        self.logger.log_error_with_recovery(
            f"Error in {self.component} for disaster {self.disaster_id}: {str(error)}",
            error_context,
            recovery_action,
            extra={'error_entry': asdict(error_entry)}
        )

    def log_dispatch_attempt(self, dispatch_id: str, mcp_tool_name: str,
                             recipients_count: int, delivery_channels: List[str]) -> None:
        """
        Log the start of an alert dispatch attempt.

        Args:
            dispatch_id: Unique identifier for the dispatch
            mcp_tool_name: Name of the MCP tool being used
            recipients_count: Number of recipients
            delivery_channels: List of delivery channels
        """
        entry = DispatchLogEntry(
            disaster_id=self.disaster_id,
            dispatch_id=dispatch_id,
            mcp_tool_name=mcp_tool_name,
            timestamp=datetime.now(),
            status="attempting",
            recipients_count=recipients_count,
            successful_deliveries=0,
            failed_deliveries=0,
            delivery_channels=delivery_channels
        )

        self.logger.log_dispatch_result(
            f"Starting alert dispatch {dispatch_id} using {mcp_tool_name} for {recipients_count} recipients",
            asdict(entry),
            extra={'dispatch_entry': asdict(entry)}
        )

    def log_dispatch_result(self, dispatch_id: str, mcp_tool_name: str,
                            recipients_count: int, successful_deliveries: int,
                            failed_deliveries: int, delivery_channels: List[str],
                            execution_time_ms: Optional[float] = None,
                            error_message: Optional[str] = None,
                            retry_count: int = 0) -> None:
        """
        Log alert dispatch results with delivery status as required by Requirement 7.3.

        Args:
            dispatch_id: Unique identifier for the dispatch
            mcp_tool_name: Name of the MCP tool used
            recipients_count: Total number of recipients
            successful_deliveries: Number of successful deliveries
            failed_deliveries: Number of failed deliveries
            delivery_channels: List of delivery channels used
            execution_time_ms: Time taken for execution in milliseconds
            error_message: Error message if dispatch failed
            retry_count: Number of retries attempted
        """
        status = "success" if failed_deliveries == 0 else "partial_failure" if successful_deliveries > 0 else "failure"

        entry = DispatchLogEntry(
            disaster_id=self.disaster_id,
            dispatch_id=dispatch_id,
            mcp_tool_name=mcp_tool_name,
            timestamp=datetime.now(),
            status=status,
            recipients_count=recipients_count,
            successful_deliveries=successful_deliveries,
            failed_deliveries=failed_deliveries,
            delivery_channels=delivery_channels,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            retry_count=retry_count
        )

        log_level = logging.INFO if status == "success" else logging.WARNING if status == "partial_failure" else logging.ERROR

        message = (
            f"Alert dispatch {dispatch_id} completed with status {status}: "
            f"{successful_deliveries}/{recipients_count} successful deliveries"
        )

        if error_message:
            message += f" - Error: {error_message}"

        self.logger.log_dispatch_result(
            message,
            asdict(entry),
            extra={'dispatch_entry': asdict(entry)}
        )

    def log_workflow_completion(self, success: bool, summary: Dict[str, Any]) -> None:
        """
        Log the completion of the entire workflow.

        Args:
            success: Whether the workflow completed successfully
            summary: Summary of workflow results
        """
        end_time = datetime.now()
        total_duration_ms = (
            end_time - self.workflow_start_time).total_seconds() * 1000

        action_type = ActionType.SUCCESS if success else ActionType.FAILURE

        entry = WorkflowLogEntry(
            disaster_id=self.disaster_id,
            workflow_step=WorkflowStep.COMPLETION,
            action_type=action_type,
            timestamp=end_time,
            component=self.component,
            message=f"Workflow {'completed successfully' if success else 'failed'} for disaster {self.disaster_id}",
            duration_ms=total_duration_ms,
            details=summary
        )

        log_level = logging.INFO if success else logging.ERROR

        self.logger.log_workflow_step(
            log_level,
            entry.message,
            entry.workflow_step.value,
            entry.action_type.value,
            extra={'workflow_entry': asdict(entry)}
        )

    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log performance metrics for monitoring and analysis.

        Args:
            metrics: Performance metrics to log
        """
        self.logger.log_performance_metrics(
            f"Performance metrics for disaster {self.disaster_id}",
            metrics,
            extra={'performance_metrics': metrics}
        )

    def create_step_logger(self, step: WorkflowStep) -> 'StepLogger':
        """
        Create a step-specific logger for detailed step logging.

        Args:
            step: The workflow step to create a logger for

        Returns:
            StepLogger instance for the specified step
        """
        return StepLogger(self, step)


class StepLogger:
    """
    Step-specific logger for detailed workflow step logging.
    """

    def __init__(self, workflow_logger: WorkflowLogger, step: WorkflowStep):
        """
        Initialize step logger.

        Args:
            workflow_logger: Parent workflow logger
            step: The workflow step this logger handles
        """
        self.workflow_logger = workflow_logger
        self.step = step
        self.step_started = False

    def __enter__(self):
        """Context manager entry - start the step."""
        self.workflow_logger.log_step_start(self.step)
        self.step_started = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - complete the step."""
        if exc_type is None:
            self.workflow_logger.log_step_success(
                self.step,
                f"Step {self.step.value} completed successfully"
            )
        else:
            self.workflow_logger.log_step_failure(self.step, exc_val)
        return False  # Don't suppress exceptions

    def log_progress(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log progress within the step."""
        self.workflow_logger.log_step_progress(self.step, message, details)

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a specific action within the step."""
        message = f"Action in {self.step.value}: {action}"
        self.workflow_logger.log_step_progress(self.step, message, details)
