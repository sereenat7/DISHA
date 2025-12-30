"""
Custom exceptions for the agentic disaster response system.
"""

from typing import Optional, Dict, Any


class DisasterResponseError(Exception):
    """Base exception for all disaster response system errors."""

    def __init__(
        self,
        message: str,
        disaster_id: Optional[str] = None,
        component: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.disaster_id = disaster_id
        self.component = component
        self.context = context or {}

    def __str__(self):
        base_msg = super().__str__()
        if self.disaster_id:
            base_msg = f"[Disaster: {self.disaster_id}] {base_msg}"
        if self.component:
            base_msg = f"[{self.component}] {base_msg}"
        return base_msg


class ContextBuildingError(DisasterResponseError):
    """Raised when context building fails."""
    pass


class PriorityAnalysisError(DisasterResponseError):
    """Raised when priority analysis fails."""
    pass


class AlertDispatchError(DisasterResponseError):
    """Raised when alert dispatch fails."""
    pass


class MCPToolError(DisasterResponseError):
    """Raised when MCP tool operations fail."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.tool_endpoint = tool_endpoint


class DataValidationError(DisasterResponseError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value


class FastAPIIntegrationError(DisasterResponseError):
    """Raised when FastAPI backend integration fails."""
    pass


class EvacuationRouteError(DisasterResponseError):
    """Raised when evacuation route operations fail."""
    pass


class ConcurrentProcessingError(DisasterResponseError):
    """Raised when concurrent disaster processing fails."""
    pass
