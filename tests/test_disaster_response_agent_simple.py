"""
Simple tests for the Disaster Response Agent to verify basic functionality.
"""

import pytest
from unittest.mock import MagicMock

from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.models.mcp_tools import MCPToolRegistry


def test_agent_initialization():
    """Test that the DisasterResponseAgent can be initialized properly."""
    mock_registry = MagicMock(spec=MCPToolRegistry)
    mock_registry.get_enabled_tools.return_value = [MagicMock()]

    config = AgentConfiguration(max_concurrent_disasters=3)
    agent = DisasterResponseAgent(mock_registry, config)

    assert agent is not None
    assert agent.config.max_concurrent_disasters == 3
    assert agent.context_builder is not None
    assert agent.alert_prioritizer is not None
    assert agent.alert_dispatcher is not None


def test_service_status_tracking():
    """Test that service status is tracked correctly."""
    mock_registry = MagicMock(spec=MCPToolRegistry)
    agent = DisasterResponseAgent(mock_registry)

    service_status = agent.get_service_status()

    assert isinstance(service_status, dict)
    assert "fastapi_backend" in service_status
    assert "mcp_tools" in service_status
    assert "context_builder" in service_status
    assert "alert_prioritizer" in service_status
    assert "alert_dispatcher" in service_status


@pytest.mark.asyncio
async def test_partial_system_failure_handling():
    """Test that partial system failures are handled gracefully."""
    mock_registry = MagicMock(spec=MCPToolRegistry)
    agent = DisasterResponseAgent(mock_registry)

    failed_components = ["fastapi_backend", "mcp_tools"]
    result = await agent.handle_partial_system_failure(failed_components)

    assert isinstance(result, dict)
    assert "can_continue_operation" in result
    assert "available_functionality" in result
    assert "degraded_functionality" in result
    assert "failed_components" in result
    assert "recovery_recommendations" in result

    assert result["failed_components"] == failed_components
    assert isinstance(result["recovery_recommendations"], list)
    assert len(result["recovery_recommendations"]) > 0


@pytest.mark.asyncio
async def test_real_time_status_reporting():
    """Test that real-time status reporting works."""
    mock_registry = MagicMock(spec=MCPToolRegistry)
    agent = DisasterResponseAgent(mock_registry)

    status = await agent.get_real_time_status()

    assert isinstance(status, dict)
    assert "timestamp" in status
    assert "system_health" in status
    assert "active_processing" in status
    assert "resource_utilization" in status

    # Verify system health structure
    system_health = status["system_health"]
    assert "overall_health" in system_health
    assert system_health["overall_health"] in [
        "healthy", "degraded", "critical", "unknown", "monitoring_failed"]

    # Verify resource utilization structure
    resource_util = status["resource_utilization"]
    assert "concurrent_slots_used" in resource_util
    assert "concurrent_slots_available" in resource_util
    assert "max_concurrent_disasters" in resource_util


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
