"""
Backup MCP tool implementations for fallback scenarios.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from agentic_disaster_response.mcp_integration import MCPTool, AlertData, ExecutionResult, ExecutionStatus
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, ToolConfiguration
from agentic_disaster_response.models.alert_priority import PriorityLevel
from agentic_disaster_response.core.exceptions import MCPToolError


class BackupAlertTool(MCPTool):
    """
    Backup implementation of Alert Tool for fallback scenarios.

    Provides basic alert functionality when primary alert tools fail.
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute backup alert delivery."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing backup alert tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for backup alert tool {self.config.tool_name}")

            # Format data for backup delivery
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Execute simplified alert delivery
            delivery_result = await self._execute_backup_delivery(formatted_data, tool_config)

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "backup_delivery_method": delivery_result["method"],
                "estimated_recipients": delivery_result["recipients"],
                "delivery_status": "completed",
                "fallback_reason": "primary_alert_tools_unavailable",
                "delivery_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Backup alert delivery completed for {alert_data.alert_id}")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Backup alert tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format alert data for backup delivery."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "message": alert_data.message,
            "disaster_type": alert_data.context.disaster_info.disaster_type.value,
            "location": alert_data.context.disaster_info.location.address,
            "affected_population": alert_data.context.affected_population.total_population,
            "timestamp": datetime.now().isoformat()
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate backup tool configuration."""
        # Backup tools have minimal configuration requirements
        return True

    async def _execute_backup_delivery(self, data: Dict[str, Any], tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute backup alert delivery method."""
        # Simulate backup delivery (e.g., local logging, file system, basic notification)
        await asyncio.sleep(0.1)

        # Log alert to local system
        self.logger.critical(
            f"EMERGENCY ALERT: {data['message']} - Location: {data['location']} - Priority: {data['priority']}")

        return {
            "method": "local_logging_and_basic_notification",
            # Limited backup reach
            "recipients": min(100, data["affected_population"]),
            "delivery_channels": ["system_log", "local_notification"]
        }


class BackupRoutingTool(MCPTool):
    """
    Backup implementation of Routing Tool for fallback scenarios.

    Provides basic routing functionality when primary routing tools fail.
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute backup routing operations."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing backup routing tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for backup routing tool {self.config.tool_name}")

            # Format data for backup routing
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Execute simplified routing operations
            routing_result = await self._execute_backup_routing(formatted_data, tool_config)

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "backup_routing_method": routing_result["method"],
                "routes_processed": routing_result["routes_count"],
                "basic_recommendations": routing_result["recommendations"],
                "fallback_reason": "primary_routing_tools_unavailable",
                "processing_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Backup routing operations completed for {alert_data.alert_id}")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Backup routing tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format routing data for backup processing."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "disaster_location": {
                "latitude": alert_data.context.disaster_info.location.latitude,
                "longitude": alert_data.context.disaster_info.location.longitude
            },
            "existing_routes": [
                {
                    "route_id": route.route_id,
                    "capacity": route.capacity,
                    "current_load": route.current_load
                }
                for route in alert_data.context.evacuation_routes
            ],
            "affected_population": alert_data.context.affected_population.total_population
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate backup routing tool configuration."""
        # Backup tools have minimal configuration requirements
        return True

    async def _execute_backup_routing(self, data: Dict[str, Any], tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute backup routing operations."""
        # Simulate basic routing analysis
        await asyncio.sleep(0.05)

        existing_routes = data["existing_routes"]
        recommendations = []

        # Basic capacity analysis
        total_capacity = sum(route["capacity"] for route in existing_routes)
        total_load = sum(route["current_load"] for route in existing_routes)

        if total_load > total_capacity * 0.8:
            recommendations.append(
                "Routes approaching capacity - consider alternative transportation")

        if len(existing_routes) < 2:
            recommendations.append(
                "Limited evacuation routes available - prioritize route clearance")

        recommendations.append(
            "Use basic navigation systems and local knowledge for routing")

        return {
            "method": "basic_capacity_analysis",
            "routes_count": len(existing_routes),
            "recommendations": recommendations,
            "capacity_utilization": total_load / max(total_capacity, 1)
        }


class BackupContextTool(MCPTool):
    """
    Backup implementation of Context Tool for fallback scenarios.

    Provides basic context management when primary context tools fail.
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute backup context operations."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing backup context tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for backup context tool {self.config.tool_name}")

            # Format data for backup context processing
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Execute simplified context operations
            context_result = await self._execute_backup_context(formatted_data, tool_config)

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "backup_context_method": context_result["method"],
                "context_summary": context_result["summary"],
                "basic_assessment": context_result["assessment"],
                "fallback_reason": "primary_context_tools_unavailable",
                "processing_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Backup context operations completed for {alert_data.alert_id}")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Backup context tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format context data for backup processing."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "disaster_type": alert_data.context.disaster_info.disaster_type.value,
            "severity": alert_data.context.disaster_info.severity.value,
            "affected_population": alert_data.context.affected_population.total_population,
            "context_completeness": alert_data.context.context_completeness,
            "available_resources": {
                "shelters": alert_data.context.available_resources.available_shelters,
                "medical_facilities": alert_data.context.available_resources.medical_facilities
            },
            "risk_score": alert_data.context.risk_assessment.overall_risk_score
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate backup context tool configuration."""
        # Backup tools have minimal configuration requirements
        return True

    async def _execute_backup_context(self, data: Dict[str, Any], tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute backup context operations."""
        # Simulate basic context analysis
        await asyncio.sleep(0.03)

        # Generate basic context summary
        summary = {
            "disaster_type": data["disaster_type"],
            "severity_level": data["severity"],
            "population_affected": data["affected_population"],
            "data_completeness": data["context_completeness"],
            "resource_availability": "limited" if data["available_resources"]["shelters"] < 3 else "adequate"
        }

        # Generate basic assessment
        assessment = []

        if data["risk_score"] > 0.7:
            assessment.append(
                "High risk situation - immediate action required")

        if data["context_completeness"] < 0.6:
            assessment.append(
                "Limited context data available - proceed with caution")

        if data["affected_population"] > 5000:
            assessment.append(
                "Large population affected - scale response accordingly")

        if data["available_resources"]["shelters"] < 2:
            assessment.append(
                "Limited shelter resources - request additional support")

        if not assessment:
            assessment.append(
                "Basic context analysis completed - standard response procedures apply")

        return {
            "method": "basic_context_analysis",
            "summary": summary,
            "assessment": assessment,
            "analysis_confidence": "low_due_to_backup_mode"
        }


class BackupNewsTool(MCPTool):
    """
    Backup implementation of News Tool for fallback scenarios.

    Provides basic news functionality when primary news tools fail.
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute backup news operations."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing backup news tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for backup news tool {self.config.tool_name}")

            # Format data for backup news processing
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Execute simplified news operations
            news_result = await self._execute_backup_news(formatted_data, tool_config)

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "backup_news_method": news_result["method"],
                "operations_completed": news_result["operations"],
                "basic_information": news_result["information"],
                "fallback_reason": "primary_news_tools_unavailable",
                "processing_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Backup news operations completed for {alert_data.alert_id}")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Backup news tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format news data for backup processing."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "disaster_type": alert_data.context.disaster_info.disaster_type.value,
            "location": alert_data.context.disaster_info.location.address,
            "severity": alert_data.context.disaster_info.severity.value,
            "timestamp": alert_data.context.disaster_info.timestamp.isoformat(),
            "affected_population": alert_data.context.affected_population.total_population
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate backup news tool configuration."""
        # Backup tools have minimal configuration requirements
        return True

    async def _execute_backup_news(self, data: Dict[str, Any], tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute backup news operations."""
        # Simulate basic news information generation
        await asyncio.sleep(0.05)

        # Generate basic disaster information
        basic_info = {
            "current_situation": f"{data['severity'].upper()} {data['disaster_type']} reported at {data['location']}",
            "emergency_bulletin": f"EMERGENCY: {data['disaster_type'].upper()} Alert - {data['location']}. Follow official evacuation orders.",
            "safety_instructions": [
                "Stay calm and follow official instructions",
                "Monitor emergency broadcasts",
                "Prepare emergency supplies",
                "Follow evacuation orders if issued"
            ],
            "contact_information": {
                "emergency_services": "911",
                "disaster_hotline": "1-800-DISASTER"
            }
        }

        operations_completed = ["basic_bulletin",
                                "safety_instructions", "emergency_contacts"]

        return {
            "method": "basic_information_generation",
            "operations": operations_completed,
            "information": basic_info,
            "data_source": "backup_templates"
        }


# Factory function to create backup tools
def create_backup_tool(tool_type: str, config: MCPToolConfig) -> MCPTool:
    """Create appropriate backup tool based on type."""
    backup_tools = {
        "alert": BackupAlertTool,
        "routing": BackupRoutingTool,
        "context": BackupContextTool,
        "news": BackupNewsTool
    }

    tool_class = backup_tools.get(tool_type.lower())
    if not tool_class:
        raise MCPToolError(f"Unknown backup tool type: {tool_type}")

    return tool_class(config)
