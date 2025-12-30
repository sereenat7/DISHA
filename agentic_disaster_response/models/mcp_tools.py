"""
MCP tool configuration and integration models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from .alert_priority import PriorityLevel


class MCPToolType(Enum):
    """Types of MCP tools available."""
    ALERT = "alert"
    ROUTING = "routing"
    CONTEXT = "context"
    COMMUNICATION = "communication"
    MONITORING = "monitoring"
    NEWS = "news"


@dataclass
class ToolConfiguration:
    """Configuration for a specific MCP tool."""
    endpoint: str
    timeout_seconds: int
    max_retries: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    authentication: Optional[Dict[str, str]] = None


@dataclass
class MCPToolConfig:
    """Configuration for MCP tools and their priority mappings."""
    tool_name: str
    tool_type: MCPToolType
    priority_mapping: Dict[PriorityLevel, ToolConfiguration]
    fallback_tools: List[str] = field(default_factory=list)
    enabled: bool = True
    description: Optional[str] = None

    def get_config_for_priority(self, priority: PriorityLevel) -> Optional[ToolConfiguration]:
        """Get tool configuration for a specific priority level."""
        return self.priority_mapping.get(priority)

    def has_priority_support(self, priority: PriorityLevel) -> bool:
        """Check if tool supports a specific priority level."""
        return priority in self.priority_mapping


@dataclass
class MCPToolRegistry:
    """Registry of all available MCP tools."""
    tools: Dict[str, MCPToolConfig] = field(default_factory=dict)

    def register_tool(self, tool_config: MCPToolConfig):
        """Register a new MCP tool."""
        self.tools[tool_config.tool_name] = tool_config

    def get_tool(self, tool_name: str) -> Optional[MCPToolConfig]:
        """Get a tool configuration by name."""
        return self.tools.get(tool_name)

    def get_tools_by_type(self, tool_type: MCPToolType) -> List[MCPToolConfig]:
        """Get all tools of a specific type."""
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]

    def get_enabled_tools(self) -> List[MCPToolConfig]:
        """Get all enabled tools."""
        return [tool for tool in self.tools.values() if tool.enabled]
