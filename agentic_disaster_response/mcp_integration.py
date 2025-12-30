"""
MCP tool integration framework with base interfaces and configuration management.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from .models.mcp_tools import MCPToolConfig, MCPToolRegistry, MCPToolType, ToolConfiguration
from .models.alert_priority import PriorityLevel, AlertPriority
from .models.context import StructuredContext
from .core.exceptions import MCPToolError, ConfigurationError


logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of MCP tool execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY_NEEDED = "retry_needed"


@dataclass
class AlertData:
    """Data structure for alert information to be sent through MCP tools."""
    alert_id: str
    priority: AlertPriority
    context: StructuredContext
    message: str
    recipients: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of MCP tool execution."""
    status: ExecutionStatus
    tool_name: str
    execution_time_ms: int
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class MCPTool(ABC):
    """Abstract base class for all MCP tools."""

    def __init__(self, config: MCPToolConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.tool_name}")

    @abstractmethod
    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute the MCP tool with given alert data and configuration."""
        pass

    @abstractmethod
    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format alert data according to tool's requirements for specific priority."""
        pass

    @abstractmethod
    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate tool configuration before execution."""
        pass

    def supports_priority(self, priority: PriorityLevel) -> bool:
        """Check if tool supports the given priority level."""
        return self.config.has_priority_support(priority)

    def get_fallback_tools(self) -> List[str]:
        """Get list of fallback tool names."""
        return self.config.fallback_tools.copy()


class MCPToolSelector:
    """Selects appropriate MCP tools based on priority levels and availability."""

    def __init__(self, registry: MCPToolRegistry):
        self.registry = registry
        self.logger = logging.getLogger(f"{__name__}.MCPToolSelector")

    def select_tools_for_priority(self, priority: PriorityLevel,
                                  tool_type: Optional[MCPToolType] = None) -> List[MCPToolConfig]:
        """Select appropriate tools for given priority level and optional tool type."""
        available_tools = self.registry.get_enabled_tools()

        if tool_type:
            available_tools = [
                tool for tool in available_tools if tool.tool_type == tool_type]

        # Filter tools that support the priority level
        suitable_tools = [
            tool for tool in available_tools
            if tool.has_priority_support(priority)
        ]

        if not suitable_tools:
            self.logger.warning(
                f"No tools found for priority {priority.value}")
            return []

        # Sort by priority mapping configuration quality (tools with more specific configs first)
        suitable_tools.sort(
            key=lambda tool: len(tool.priority_mapping),
            reverse=True
        )

        self.logger.info(
            f"Selected {len(suitable_tools)} tools for priority {priority.value}")
        return suitable_tools

    def get_fallback_tools(self, primary_tool: MCPToolConfig,
                           priority: PriorityLevel) -> List[MCPToolConfig]:
        """Get fallback tools for a primary tool that failed."""
        fallback_names = primary_tool.fallback_tools
        fallback_tools = []

        for tool_name in fallback_names:
            tool = self.registry.get_tool(tool_name)
            if tool and tool.enabled and tool.has_priority_support(priority):
                fallback_tools.append(tool)

        self.logger.info(
            f"Found {len(fallback_tools)} fallback tools for {primary_tool.tool_name}")
        return fallback_tools


class MCPDataFormatter:
    """Formats alert data for different MCP tool requirements."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MCPDataFormatter")

    def format_for_tool(self, alert_data: AlertData, tool_config: MCPToolConfig,
                        priority: PriorityLevel) -> Dict[str, Any]:
        """Format alert data for specific tool and priority level."""
        tool_configuration = tool_config.get_config_for_priority(priority)
        if not tool_configuration:
            raise ConfigurationError(
                f"No configuration found for tool {tool_config.tool_name} at priority {priority.value}"
            )

        # Base formatting common to all tools
        base_data = {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "priority_score": alert_data.priority.score,
            "message": alert_data.message,
            "timestamp": alert_data.context.disaster_info.timestamp.isoformat(),
            "disaster_type": alert_data.context.disaster_info.disaster_type.value,
            "location": {
                "latitude": alert_data.context.disaster_info.location.latitude,
                "longitude": alert_data.context.disaster_info.location.longitude,
                "address": alert_data.context.disaster_info.location.address
            }
        }

        # Add tool-specific formatting based on tool type
        if tool_config.tool_type == MCPToolType.ALERT:
            return self._format_for_alert_tool(base_data, alert_data, tool_configuration)
        elif tool_config.tool_type == MCPToolType.ROUTING:
            return self._format_for_routing_tool(base_data, alert_data, tool_configuration)
        elif tool_config.tool_type == MCPToolType.CONTEXT:
            return self._format_for_context_tool(base_data, alert_data, tool_configuration)
        elif tool_config.tool_type == MCPToolType.NEWS:
            return self._format_for_news_tool(base_data, alert_data, tool_configuration)
        else:
            # Generic formatting for other tool types
            return self._format_generic(base_data, alert_data, tool_configuration)

    def _format_for_alert_tool(self, base_data: Dict[str, Any], alert_data: AlertData,
                               config: ToolConfiguration) -> Dict[str, Any]:
        """Format data specifically for alert tools."""
        formatted_data = base_data.copy()
        formatted_data.update({
            "recipients": alert_data.recipients,
            "channels": alert_data.channels,
            "urgency": self._map_priority_to_urgency(alert_data.priority.level),
            "estimated_response_time": alert_data.priority.estimated_response_time.total_seconds(),
            "required_resources": [resource.value for resource in alert_data.priority.required_resources]
        })

        # Add configuration-specific parameters
        formatted_data.update(config.parameters)
        return formatted_data

    def _format_for_routing_tool(self, base_data: Dict[str, Any], alert_data: AlertData,
                                 config: ToolConfiguration) -> Dict[str, Any]:
        """Format data specifically for routing tools."""
        formatted_data = base_data.copy()
        formatted_data.update({
            "evacuation_routes": [
                {
                    "route_id": route.route_id,
                    "start": {"lat": route.start_location.latitude, "lng": route.start_location.longitude},
                    "end": {"lat": route.end_location.latitude, "lng": route.end_location.longitude},
                    "distance_km": route.distance_km,
                    "estimated_time_minutes": route.estimated_time_minutes,
                    "capacity": route.capacity,
                    "current_load": route.current_load
                }
                for route in alert_data.context.evacuation_routes
            ],
            "affected_population": alert_data.context.affected_population.total_population,
            "safe_locations": [
                {"lat": loc.latitude, "lng": loc.longitude, "address": loc.address}
                for loc in alert_data.context.geographical_context.safe_locations
            ]
        })

        formatted_data.update(config.parameters)
        return formatted_data

    def _format_for_context_tool(self, base_data: Dict[str, Any], alert_data: AlertData,
                                 config: ToolConfiguration) -> Dict[str, Any]:
        """Format data specifically for context tools."""
        formatted_data = base_data.copy()
        formatted_data.update({
            "context_completeness": alert_data.context.context_completeness,
            "missing_data": alert_data.context.missing_data_indicators,
            "risk_metrics": {
                "overall_risk": alert_data.context.risk_assessment.overall_risk_score,
                "evacuation_difficulty": alert_data.context.risk_assessment.evacuation_difficulty,
                "time_criticality": alert_data.context.risk_assessment.time_criticality,
                "resource_availability": alert_data.context.risk_assessment.resource_availability
            },
            "available_resources": {
                "shelters": alert_data.context.available_resources.available_shelters,
                "shelter_capacity": alert_data.context.available_resources.shelter_capacity,
                "medical_facilities": alert_data.context.available_resources.medical_facilities,
                "emergency_vehicles": alert_data.context.available_resources.emergency_vehicles
            }
        })

        formatted_data.update(config.parameters)
        return formatted_data

    def _format_for_news_tool(self, base_data: Dict[str, Any], alert_data: AlertData,
                              config: ToolConfiguration) -> Dict[str, Any]:
        """Format data specifically for news tools."""
        formatted_data = base_data.copy()
        formatted_data.update({
            "operations": config.parameters.get("operations", ["current_disasters"]),
            "severity": alert_data.context.disaster_info.severity.value,
            "affected_population": alert_data.context.affected_population.total_population,
            "evacuation_routes_available": len(alert_data.context.evacuation_routes),
            "administrative_area": alert_data.context.disaster_info.location.administrative_area
        })

        formatted_data.update(config.parameters)
        return formatted_data

    def _format_generic(self, base_data: Dict[str, Any], alert_data: AlertData,
                        config: ToolConfiguration) -> Dict[str, Any]:
        """Generic formatting for unspecified tool types."""
        formatted_data = base_data.copy()
        formatted_data.update({
            "metadata": alert_data.metadata,
            "context_summary": {
                "completeness": alert_data.context.context_completeness,
                "population_affected": alert_data.context.affected_population.total_population,
                "routes_available": len(alert_data.context.evacuation_routes)
            }
        })

        formatted_data.update(config.parameters)
        return formatted_data

    def _map_priority_to_urgency(self, priority: PriorityLevel) -> str:
        """Map priority level to urgency string for external tools."""
        mapping = {
            PriorityLevel.CRITICAL: "immediate",
            PriorityLevel.HIGH: "urgent",
            PriorityLevel.MEDIUM: "normal",
            PriorityLevel.LOW: "routine"
        }
        return mapping.get(priority, "normal")


class MCPConfigurationManager:
    """Manages MCP tool configurations and registry."""

    def __init__(self):
        self.registry = MCPToolRegistry()
        self.logger = logging.getLogger(f"{__name__}.MCPConfigurationManager")

    def load_default_configurations(self) -> None:
        """Load default MCP tool configurations."""
        # Default Alert Tool Configuration
        alert_tool = MCPToolConfig(
            tool_name="default_alert_tool",
            tool_type=MCPToolType.ALERT,
            priority_mapping={
                PriorityLevel.CRITICAL: ToolConfiguration(
                    endpoint="mcp://alert/critical",
                    timeout_seconds=30,
                    max_retries=3,
                    parameters={
                        "channels": ["emergency_broadcast", "mobile_push", "sms", "voice_call", "email"],
                        "broadcast_radius_km": 15,
                        "escalate": True
                    }
                ),
                PriorityLevel.HIGH: ToolConfiguration(
                    endpoint="mcp://alert/high",
                    timeout_seconds=60,
                    max_retries=2,
                    parameters={
                        "channels": ["mobile_push", "sms", "email"],
                        "broadcast_radius_km": 10,
                        "escalate": False
                    }
                ),
                PriorityLevel.MEDIUM: ToolConfiguration(
                    endpoint="mcp://alert/medium",
                    timeout_seconds=120,
                    max_retries=1,
                    parameters={
                        "channels": ["mobile_push", "email", "web_notification"],
                        "broadcast_radius_km": 5,
                        "escalate": False
                    }
                ),
                PriorityLevel.LOW: ToolConfiguration(
                    endpoint="mcp://alert/low",
                    timeout_seconds=300,
                    max_retries=1,
                    parameters={
                        "channels": ["email", "web_notification"],
                        "broadcast_radius_km": 3,
                        "escalate": False
                    }
                )
            },
            fallback_tools=["backup_alert_tool"],
            description="Default alert notification tool"
        )

        # Default Routing Tool Configuration
        routing_tool = MCPToolConfig(
            tool_name="default_routing_tool",
            tool_type=MCPToolType.ROUTING,
            priority_mapping={
                PriorityLevel.CRITICAL: ToolConfiguration(
                    endpoint="mcp://routing/critical",
                    timeout_seconds=45,
                    max_retries=3,
                    parameters={
                        "operations": ["primary_routing", "alternative_routing", "real_time_updates", "capacity_monitoring", "navigation_integration"],
                        "max_alternative_routes": 3,
                        "real_time_updates": True
                    }
                ),
                PriorityLevel.HIGH: ToolConfiguration(
                    endpoint="mcp://routing/high",
                    timeout_seconds=90,
                    max_retries=2,
                    parameters={
                        "operations": ["primary_routing", "alternative_routing", "real_time_updates", "navigation_integration"],
                        "max_alternative_routes": 2,
                        "real_time_updates": True
                    }
                ),
                PriorityLevel.MEDIUM: ToolConfiguration(
                    endpoint="mcp://routing/medium",
                    timeout_seconds=180,
                    max_retries=1,
                    parameters={
                        "operations": ["primary_routing", "alternative_routing", "capacity_monitoring"],
                        "max_alternative_routes": 1,
                        "real_time_updates": False
                    }
                )
            },
            fallback_tools=["backup_routing_tool"],
            description="Default evacuation routing tool"
        )

        # Default Context Tool Configuration
        context_tool = MCPToolConfig(
            tool_name="default_context_tool",
            tool_type=MCPToolType.CONTEXT,
            priority_mapping={
                PriorityLevel.CRITICAL: ToolConfiguration(
                    endpoint="mcp://context/critical",
                    timeout_seconds=30,
                    max_retries=2,
                    parameters={
                        "operations": ["data_collection", "situational_awareness", "data_validation", "context_sharing", "historical_analysis"],
                        "data_sources": ["weather_service", "traffic_service", "social_media", "sensor_network"],
                        "sharing_targets": ["emergency_services", "local_government", "media_outlets", "public_systems"],
                        "detailed_analysis": True,
                        "real_time_data": True
                    }
                ),
                PriorityLevel.HIGH: ToolConfiguration(
                    endpoint="mcp://context/high",
                    timeout_seconds=60,
                    max_retries=2,
                    parameters={
                        "operations": ["data_collection", "situational_awareness", "data_validation", "context_sharing"],
                        "data_sources": ["weather_service", "traffic_service", "social_media"],
                        "sharing_targets": ["emergency_services", "local_government"],
                        "detailed_analysis": True,
                        "real_time_data": False
                    }
                ),
                PriorityLevel.MEDIUM: ToolConfiguration(
                    endpoint="mcp://context/medium",
                    timeout_seconds=120,
                    max_retries=1,
                    parameters={
                        "operations": ["data_collection", "data_validation", "context_sharing"],
                        "data_sources": ["weather_service", "traffic_service"],
                        "sharing_targets": ["emergency_services"],
                        "detailed_analysis": False,
                        "real_time_data": False
                    }
                )
            },
            fallback_tools=["backup_context_tool"],
            description="Default context management tool"
        )

        # Default News Tool Configuration
        news_tool = MCPToolConfig(
            tool_name="default_news_tool",
            tool_type=MCPToolType.NEWS,
            priority_mapping={
                PriorityLevel.CRITICAL: ToolConfiguration(
                    endpoint="mcp://news/critical",
                    timeout_seconds=45,
                    max_retries=2,
                    parameters={"operations": [
                        "current_disasters", "emergency_bulletin", "safety_instructions"]}
                ),
                PriorityLevel.HIGH: ToolConfiguration(
                    endpoint="mcp://news/high",
                    timeout_seconds=60,
                    max_retries=2,
                    parameters={"operations": [
                        "disaster_context", "emergency_bulletin"]}
                ),
                PriorityLevel.MEDIUM: ToolConfiguration(
                    endpoint="mcp://news/medium",
                    timeout_seconds=90,
                    max_retries=1,
                    parameters={"operations": [
                        "current_disasters", "disaster_context"]}
                ),
                PriorityLevel.LOW: ToolConfiguration(
                    endpoint="mcp://news/low",
                    timeout_seconds=120,
                    max_retries=1,
                    parameters={"operations": ["current_disasters"]}
                )
            },
            fallback_tools=[],
            description="News and information tool using Groq AI"
        )

        # Register all default tools
        self.registry.register_tool(alert_tool)
        self.registry.register_tool(routing_tool)
        self.registry.register_tool(context_tool)
        self.registry.register_tool(news_tool)

        self.logger.info("Loaded default MCP tool configurations")

    def add_tool_configuration(self, tool_config: MCPToolConfig) -> None:
        """Add a new tool configuration to the registry."""
        self.registry.register_tool(tool_config)
        self.logger.info(f"Added tool configuration: {tool_config.tool_name}")

    def get_registry(self) -> MCPToolRegistry:
        """Get the tool registry."""
        return self.registry

    def validate_all_configurations(self) -> Dict[str, List[str]]:
        """Validate all tool configurations and return any errors."""
        validation_errors = {}

        for tool_name, tool_config in self.registry.tools.items():
            errors = []

            # Check if tool has at least one priority mapping
            if not tool_config.priority_mapping:
                errors.append("No priority mappings defined")

            # Validate each priority configuration
            for priority, config in tool_config.priority_mapping.items():
                if not config.endpoint:
                    errors.append(
                        f"No endpoint defined for priority {priority.value}")
                if config.timeout_seconds <= 0:
                    errors.append(
                        f"Invalid timeout for priority {priority.value}")
                if config.max_retries < 0:
                    errors.append(
                        f"Invalid max_retries for priority {priority.value}")

            if errors:
                validation_errors[tool_name] = errors

        return validation_errors
