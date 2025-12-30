"""
Factory for creating concrete MCP tool instances.
"""

import logging
from typing import Dict, Type

from agentic_disaster_response.mcp_integration import MCPTool
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, MCPToolType
from agentic_disaster_response.core.exceptions import MCPToolError

from .alert_tool import AlertMCPTool
from .routing_tool import RoutingMCPTool
from .context_tool import ContextMCPTool
from .news_tool import NewsMCPTool
from .backup_tools import BackupAlertTool, BackupRoutingTool, BackupContextTool, BackupNewsTool


logger = logging.getLogger(__name__)


class MCPToolFactory:
    """Factory for creating concrete MCP tool instances."""

    # Mapping of tool types to their concrete implementations
    TOOL_IMPLEMENTATIONS: Dict[MCPToolType, Type[MCPTool]] = {
        MCPToolType.ALERT: AlertMCPTool,
        MCPToolType.ROUTING: RoutingMCPTool,
        MCPToolType.CONTEXT: ContextMCPTool,
        MCPToolType.NEWS: NewsMCPTool
    }

    # Mapping of backup tool types
    BACKUP_TOOL_IMPLEMENTATIONS: Dict[MCPToolType, Type[MCPTool]] = {
        MCPToolType.ALERT: BackupAlertTool,
        MCPToolType.ROUTING: BackupRoutingTool,
        MCPToolType.CONTEXT: BackupContextTool,
        MCPToolType.NEWS: BackupNewsTool
    }

    @classmethod
    def create_tool(cls, config: MCPToolConfig, use_backup: bool = False) -> MCPTool:
        """
        Create a concrete MCP tool instance based on configuration.

        Args:
            config: MCP tool configuration
            use_backup: Whether to create backup implementation

        Returns:
            Concrete MCP tool instance

        Raises:
            MCPToolError: If tool type is not supported
        """
        tool_implementations = cls.BACKUP_TOOL_IMPLEMENTATIONS if use_backup else cls.TOOL_IMPLEMENTATIONS

        tool_class = tool_implementations.get(config.tool_type)
        if not tool_class:
            available_types = list(tool_implementations.keys())
            raise MCPToolError(
                f"Unsupported tool type: {config.tool_type}. "
                f"Available types: {[t.value for t in available_types]}"
            )

        try:
            tool_instance = tool_class(config)
            logger.info(
                f"Created {'backup ' if use_backup else ''}{config.tool_type.value} tool: {config.tool_name}")
            return tool_instance

        except Exception as e:
            logger.error(f"Failed to create tool {config.tool_name}: {e}")
            raise MCPToolError(
                f"Failed to create tool {config.tool_name}: {e}") from e

    @classmethod
    def create_tools_from_registry(cls, registry, use_backup: bool = False) -> Dict[str, MCPTool]:
        """
        Create all tools from a registry.

        Args:
            registry: MCPToolRegistry instance
            use_backup: Whether to create backup implementations

        Returns:
            Dictionary mapping tool names to tool instances
        """
        tools = {}

        for tool_name, tool_config in registry.tools.items():
            if not tool_config.enabled:
                logger.info(f"Skipping disabled tool: {tool_name}")
                continue

            try:
                tool_instance = cls.create_tool(tool_config, use_backup)
                tools[tool_name] = tool_instance

            except Exception as e:
                logger.error(f"Failed to create tool {tool_name}: {e}")
                # Continue creating other tools even if one fails
                continue

        logger.info(
            f"Created {len(tools)} {'backup ' if use_backup else ''}tools from registry")
        return tools

    @classmethod
    def get_supported_tool_types(cls, include_backup: bool = True) -> list:
        """
        Get list of supported tool types.

        Args:
            include_backup: Whether to include backup tool types

        Returns:
            List of supported MCPToolType values
        """
        primary_types = list(cls.TOOL_IMPLEMENTATIONS.keys())

        if include_backup:
            backup_types = list(cls.BACKUP_TOOL_IMPLEMENTATIONS.keys())
            # Combine and deduplicate
            all_types = list(set(primary_types + backup_types))
            return all_types

        return primary_types

    @classmethod
    def validate_tool_config(cls, config: MCPToolConfig) -> bool:
        """
        Validate that a tool configuration is supported.

        Args:
            config: MCP tool configuration to validate

        Returns:
            True if configuration is valid and supported
        """
        # Check if tool type is supported
        if config.tool_type not in cls.TOOL_IMPLEMENTATIONS:
            logger.error(f"Unsupported tool type: {config.tool_type}")
            return False

        # Check if tool has required configuration
        if not config.priority_mapping:
            logger.error(f"Tool {config.tool_name} has no priority mappings")
            return False

        # Validate priority configurations
        for priority, tool_config in config.priority_mapping.items():
            if not tool_config.endpoint:
                logger.error(
                    f"Tool {config.tool_name} missing endpoint for priority {priority.value}")
                return False

            if tool_config.timeout_seconds <= 0:
                logger.error(
                    f"Tool {config.tool_name} has invalid timeout for priority {priority.value}")
                return False

        return True


def create_default_tool_registry():
    """
    Create a default MCP tool registry with concrete tool implementations.

    Returns:
        MCPToolRegistry with default tools configured
    """
    from agentic_disaster_response.models.mcp_tools import MCPToolRegistry
    from agentic_disaster_response.mcp_integration import MCPConfigurationManager

    # Create configuration manager and load defaults
    config_manager = MCPConfigurationManager()
    config_manager.load_default_configurations()

    # Get the registry
    registry = config_manager.get_registry()

    # Validate all configurations
    validation_errors = config_manager.validate_all_configurations()
    if validation_errors:
        logger.warning(
            f"Tool configuration validation errors: {validation_errors}")

    logger.info(
        f"Created default tool registry with {len(registry.tools)} tools")
    return registry


def create_concrete_tools_registry():
    """
    Create a registry with concrete tool instances ready for use.

    Returns:
        Dictionary mapping tool names to concrete tool instances
    """
    # Create default registry
    registry = create_default_tool_registry()

    # Create concrete tool instances
    concrete_tools = MCPToolFactory.create_tools_from_registry(registry)

    # Also create backup tools
    backup_tools = MCPToolFactory.create_tools_from_registry(
        registry, use_backup=True)

    # Add backup suffix to backup tool names to avoid conflicts
    backup_tools_renamed = {
        f"{name}_backup": tool for name, tool in backup_tools.items()
    }

    # Combine primary and backup tools
    all_tools = {**concrete_tools, **backup_tools_renamed}

    logger.info(
        f"Created concrete tools registry with {len(all_tools)} total tools")
    return all_tools, registry
