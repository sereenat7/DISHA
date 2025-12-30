"""
Property-based tests for the Disaster Response Agent.
"""

import asyncio
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite
from unittest.mock import MagicMock, patch

from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.models.disaster_data import (
    DisasterData, DisasterType, SeverityLevel, ProcessingStatus,
    GeographicalArea, ImpactAssessment
)
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.mcp_tools import MCPToolRegistry


@composite
def disaster_data_strategy(draw):
    """Generate valid DisasterData for property testing."""
    disaster_types = list(DisasterType)
    severity_levels = list(SeverityLevel)

    disaster_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'))))
    disaster_type = draw(st.sampled_from(disaster_types))
    severity = draw(st.sampled_from(severity_levels))

    # Generate location with valid coordinates
    latitude = draw(st.floats(min_value=-89.0, max_value=89.0))
    longitude = draw(st.floats(min_value=-179.0, max_value=179.0))
    location = Location(
        latitude=latitude,
        longitude=longitude,
        address=draw(st.text(min_size=1, max_size=50)),
        administrative_area=draw(st.text(min_size=1, max_size=20))
    )

    # Generate affected areas
    affected_areas = []
    area_location = Location(
        latitude=latitude + 0.01,
        longitude=longitude + 0.01,
        address="Area 1",
        administrative_area="affected_zone"
    )
    affected_areas.append(GeographicalArea(
        center=area_location,
        radius_km=1.0,
        area_name="Affected Area 1"
    ))

    # Generate impact assessment
    affected_population = draw(st.integers(min_value=1, max_value=5000))
    impact = ImpactAssessment(
        estimated_affected_population=affected_population,
        estimated_casualties=0,
        infrastructure_damage_level=severity
    )

    return DisasterData(
        disaster_id=disaster_id,
        disaster_type=disaster_type,
        location=location,
        severity=severity,
        timestamp=datetime.now(),
        affected_areas=affected_areas,
        estimated_impact=impact,
        description="Test disaster",
        source="test_generator"
    )


class TestDisasterResponseAgentProperties:
    """Property-based tests for DisasterResponseAgent."""

    @given(disaster_data_strategy())
    @settings(max_examples=5, deadline=30000)
    @pytest.mark.asyncio
    async def test_workflow_progression_property(self, disaster_data):
        """
        **Feature: agentic-disaster-response, Property 3: Workflow Progression**
        
        For any valid disaster data, the agent should initiate the context building 
        process and progress through the complete workflow to alert dispatch.
        
        **Validates: Requirements 1.4, 5.2**
        """
        # Setup
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_enabled_tools.return_value = [MagicMock()]
        
        agent = DisasterResponseAgent(mock_registry)
        
        # Mock the external dependencies
        with patch('agentic_disaster_response.disaster_response_agent.get_disaster_data') as mock_get_data, \
             patch.object(agent.context_builder, 'build_context') as mock_build_context, \
             patch.object(agent.alert_prioritizer, 'analyze_priority_with_fallback') as mock_analyze_priority, \
             patch.object(agent.alert_dispatcher, 'dispatch_alerts') as mock_dispatch:
            
            # Setup mocks
            mock_get_data.return_value = disaster_data
            
            # Mock context
            mock_context = MagicMock()
            mock_context.disaster_info = disaster_data
            mock_context.context_completeness = 0.8
            mock_context.affected_population.total_population = disaster_data.estimated_impact.estimated_affected_population
            mock_build_context.return_value = mock_context
            
            # Mock priority
            mock_priority = MagicMock()
            mock_priority.level.value = "high"
            mock_priority.score = 0.7
            mock_analyze_priority.return_value = mock_priority
            
            # Mock dispatch result
            mock_dispatch_result = MagicMock()
            mock_dispatch_result.success = True
            mock_dispatch_result.execution_results = []
            mock_dispatch_result.successful_dispatches = 1
            mock_dispatch_result.total_tools_attempted = 1
            mock_dispatch.return_value = mock_dispatch_result
            
            # Execute
            response = await agent.process_disaster_event(disaster_data.disaster_id)
            
            # Verify workflow progression
            assert response.disaster_id == disaster_data.disaster_id
            assert response.processing_status == ProcessingStatus.COMPLETED.value
            assert response.context is not None
            assert response.priority is not None
            assert response.completion_time is not None
            
            # Verify all workflow steps were called
            mock_get_data.assert_called_once_with(disaster_data.disaster_id)
            mock_build_context.assert_called_once()
            mock_analyze_priority.assert_called_once()
            mock_dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_and_connection_management_property(self):
        """
        **Feature: agentic-disaster-response, Property 10: Initialization and Connection Management**
        
        For any agent initialization, all required connections to services and MCP tools 
        should be established successfully.
        
        **Validates: Requirements 5.1**
        """
        # Setup
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_enabled_tools.return_value = [MagicMock()]
        
        config = AgentConfiguration(max_concurrent_disasters=3)
        agent = DisasterResponseAgent(mock_registry, config)
        
        # Mock external service connections
        with patch.object(agent, '_test_fastapi_connection') as mock_fastapi, \
             patch.object(agent, '_test_mcp_tools_connection') as mock_mcp:
            
            mock_fastapi.return_value = True
            mock_mcp.return_value = True
            
            # Execute initialization
            connection_results = await agent.initialize_connections()
            
            # Verify all required connections are established
            assert isinstance(connection_results, dict)
            assert "fastapi_backend" in connection_results
            assert "mcp_tools" in connection_results
            assert "context_builder" in connection_results
            assert "alert_prioritizer" in connection_results
            assert "alert_dispatcher" in connection_results
            
            # Verify critical services are connected
            critical_services = ["fastapi_backend", "context_builder", "alert_prioritizer"]
            for service in critical_services:
                assert connection_results[service] is True, f"Critical service {service} not connected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])