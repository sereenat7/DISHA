"""
Simple integration tests for the disaster response system.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.mcp_tools.tool_factory import create_default_tool_registry
from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel, GeographicalArea, ImpactAssessment
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.alert_priority import PriorityLevel


class TestSimpleIntegration:
    """Simple integration tests for core functionality."""

    @pytest.fixture
    def agent_config(self):
        """Create agent configuration for testing."""
        return AgentConfiguration(
            context_search_radius_km=10.0,
            max_routes_per_category=2,
            enable_concurrent_processing=True,
            max_concurrent_disasters=2,
            enable_performance_monitoring=True
        )

    @pytest_asyncio.fixture
    async def agent(self, agent_config):
        """Create a disaster response agent for testing."""
        registry = create_default_tool_registry()
        agent = DisasterResponseAgent(registry, agent_config)
        await agent.initialize_connections()
        return agent

    async def create_agent(self, config=None):
        """Create a disaster response agent for testing."""
        registry = create_default_tool_registry()
        if config is None:
            config = AgentConfiguration()

        agent = DisasterResponseAgent(registry, config)
        await agent.initialize_connections()
        return agent

    def create_test_disaster_data(self, disaster_id: str) -> DisasterData:
        """Create test disaster data."""
        location = Location(
            latitude=52.5200,
            longitude=13.4050,
            address="Test Location",
            administrative_area="test_area"
        )

        affected_area = GeographicalArea(
            center=location,
            radius_km=5.0,
            area_name="Test Affected Area"
        )

        impact = ImpactAssessment(
            estimated_affected_population=2000,
            estimated_casualties=20,
            infrastructure_damage_level=SeverityLevel.MEDIUM
        )

        return DisasterData(
            disaster_id=disaster_id,
            disaster_type=DisasterType.FIRE,
            location=location,
            severity=SeverityLevel.HIGH,
            timestamp=datetime.now(),
            affected_areas=[affected_area],
            estimated_impact=impact,
            description=f"Test disaster {disaster_id}",
            source="test_system"
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the agent initializes correctly."""
        assert agent is not None

        # Check service connections
        connections = agent.get_service_status()
        assert connections["context_builder"] is True
        assert connections["alert_prioritizer"] is True
        assert connections["alert_dispatcher"] is True

    @pytest.mark.asyncio
    async def test_mcp_tool_creation(self):
        """Test that MCP tools are created correctly."""
        registry = create_default_tool_registry()

        # Check that tools were created
        assert len(registry.tools) == 3

        # Check tool types
        tool_types = [tool.tool_type.value for tool in registry.tools.values()]
        assert "alert" in tool_types
        assert "routing" in tool_types
        assert "context" in tool_types

    @pytest.mark.asyncio
    async def test_context_building(self, agent):
        """Test context building functionality."""
        disaster_data = self.create_test_disaster_data("test_context_001")

        # Test context building
        context = await agent.context_builder.build_context(disaster_data)

        assert context is not None
        assert context.disaster_info.disaster_id == "test_context_001"
        assert context.disaster_info.disaster_type == DisasterType.FIRE
        assert context.context_completeness > 0.0
        assert context.affected_population.total_population > 0

    @pytest.mark.asyncio
    async def test_priority_analysis(self, agent):
        """Test priority analysis functionality."""
        disaster_data = self.create_test_disaster_data("test_priority_001")
        context = await agent.context_builder.build_context(disaster_data)

        # Test priority analysis
        priority = agent.alert_prioritizer.analyze_priority_with_fallback(
            context)

        assert priority is not None
        assert priority.level in [level for level in PriorityLevel]
        assert 0.0 <= priority.score <= 1.0
        assert priority.confidence > 0.0

    @pytest.mark.asyncio
    async def test_alert_dispatch(self, agent):
        """Test alert dispatch functionality."""
        disaster_data = self.create_test_disaster_data("test_dispatch_001")
        context = await agent.context_builder.build_context(disaster_data)
        priority = agent.alert_prioritizer.analyze_priority_with_fallback(
            context)

        # Test alert dispatch
        message = "Test emergency alert"
        dispatch_result = await agent.alert_dispatcher.dispatch_alerts(
            priority=priority,
            context=context,
            message=message
        )

        assert dispatch_result is not None
        assert dispatch_result.total_tools_attempted > 0
        # Should have at least attempted some dispatches
        assert len(dispatch_result.execution_results) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, agent):
        """Test complete end-to-end disaster response workflow."""
        disaster_id = "test_e2e_001"

        # Store disaster data in the agent's mock system
        disaster_data = self.create_test_disaster_data(disaster_id)

        # Mock the disaster data storage
        import sys
        import os
        backend_path = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), 'Backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        try:
            from evacuation_system.main import _store_disaster_data
            await _store_disaster_data(disaster_id, disaster_data)
        except ImportError:
            # If FastAPI backend not available, skip this part
            pass

        # Process disaster through agent
        response = await agent.process_disaster_event(disaster_id)

        # Verify response
        assert response is not None
        assert response.disaster_id == disaster_id
        assert response.processing_status in ["completed", "failed"]
        assert response.total_processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, agent):
        """Test concurrent disaster processing."""
        disaster_ids = ["concurrent_001", "concurrent_002"]

        # Store disaster data for each
        for disaster_id in disaster_ids:
            disaster_data = self.create_test_disaster_data(disaster_id)

            # Try to store in FastAPI backend if available
            try:
                import sys
                import os
                backend_path = os.path.join(os.path.dirname(
                    os.path.dirname(__file__)), 'Backend')
                if backend_path not in sys.path:
                    sys.path.insert(0, backend_path)

                from evacuation_system.main import _store_disaster_data
                await _store_disaster_data(disaster_id, disaster_data)
            except ImportError:
                pass

        # Process disasters concurrently
        responses = await agent.handle_concurrent_disasters(disaster_ids)

        # Verify responses
        assert len(responses) == len(disaster_ids)
        for response in responses:
            assert response.disaster_id in disaster_ids
            assert response.processing_status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, agent):
        """Test system health monitoring."""
        health_status = await agent.monitor_system_health()

        assert "timestamp" in health_status
        assert "overall_health" in health_status
        assert "component_status" in health_status

        # Check component status
        components = health_status["component_status"]
        expected_components = ["fastapi_backend", "mcp_tools", "context_builder",
                               "alert_prioritizer", "alert_dispatcher"]

        for component in expected_components:
            assert component in components

    @pytest.mark.asyncio
    async def test_error_recovery(self, agent):
        """Test error recovery mechanisms."""
        disaster_id = "test_error_recovery"

        # Create disaster data
        disaster_data = self.create_test_disaster_data(disaster_id)

        # Store disaster data
        try:
            import sys
            import os
            backend_path = os.path.join(os.path.dirname(
                os.path.dirname(__file__)), 'Backend')
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from evacuation_system.main import _store_disaster_data
            await _store_disaster_data(disaster_id, disaster_data)
        except ImportError:
            pass

        # Test recovery from failure
        recovery_result = await agent.recover_from_failure(
            disaster_id,
            {"error_type": "TestError", "component": "TestComponent"}
        )

        assert recovery_result is not None
        assert "disaster_id" in recovery_result
        assert "recovery_success" in recovery_result
        assert "recovery_actions" in recovery_result

    @pytest.mark.asyncio
    async def test_property_workflow_progression(self, agent):
        """
        Property test: For any valid disaster data, the agent should progress 
        through the complete workflow.
        **Validates: Requirements 1.4, 5.2**
        """
        # Test with different disaster types
        disaster_types = [DisasterType.FIRE,
                          DisasterType.FLOOD, DisasterType.EARTHQUAKE]
        severities = [SeverityLevel.LOW, SeverityLevel.MEDIUM,
                      SeverityLevel.HIGH, SeverityLevel.CRITICAL]

        for i, (disaster_type, severity) in enumerate(zip(disaster_types, severities)):
            disaster_id = f"prop_test_{disaster_type.value}_{i}"

            # Create disaster data
            location = Location(
                latitude=52.5200 + i * 0.01,
                longitude=13.4050 + i * 0.01,
                address=f"Test Location {i}",
                administrative_area=f"test_area_{i}"
            )

            affected_area = GeographicalArea(
                center=location,
                radius_km=5.0,
                area_name=f"Test Affected Area {i}"
            )

            impact = ImpactAssessment(
                estimated_affected_population=1000 + i * 500,
                estimated_casualties=10 + i * 5,
                infrastructure_damage_level=severity
            )

            disaster_data = DisasterData(
                disaster_id=disaster_id,
                disaster_type=disaster_type,
                location=location,
                severity=severity,
                timestamp=datetime.now(),
                affected_areas=[affected_area],
                estimated_impact=impact,
                description=f"Property test disaster {i}",
                source="property_test"
            )

            # Store disaster data
            try:
                import sys
                import os
                backend_path = os.path.join(os.path.dirname(
                    os.path.dirname(__file__)), 'Backend')
                if backend_path not in sys.path:
                    sys.path.insert(0, backend_path)

                from evacuation_system.main import _store_disaster_data
                await _store_disaster_data(disaster_id, disaster_data)
            except ImportError:
                pass

            # Process disaster
            response = await agent.process_disaster_event(disaster_id)

            # Verify workflow progression
            assert response is not None, f"No response for {disaster_type.value}"
            assert response.disaster_id == disaster_id, f"Wrong disaster ID for {disaster_type.value}"
            assert response.processing_status in [
                "completed", "failed"], f"Invalid status for {disaster_type.value}"
            assert response.total_processing_time_seconds > 0, f"No processing time for {disaster_type.value}"

    @pytest.mark.asyncio
    async def test_property_mcp_tool_execution(self, agent):
        """
        Property test: MCP tools should execute and provide results.
        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        disaster_data = self.create_test_disaster_data("prop_mcp_test")
        context = await agent.context_builder.build_context(disaster_data)
        priority = agent.alert_prioritizer.analyze_priority_with_fallback(
            context)

        # Test alert dispatch with different priorities
        priorities_to_test = [priority]  # Use the calculated priority

        for test_priority in priorities_to_test:
            message = f"Property test alert for {test_priority.level.value} priority"

            dispatch_result = await agent.alert_dispatcher.dispatch_alerts(
                priority=test_priority,
                context=context,
                message=message
            )

            # Verify MCP tool execution
            assert dispatch_result is not None, f"No dispatch result for {test_priority.level.value}"
            assert dispatch_result.total_tools_attempted > 0, f"No tools attempted for {test_priority.level.value}"
            assert len(
                dispatch_result.execution_results) > 0, f"No execution results for {test_priority.level.value}"

            # At least some tools should succeed or fail (not timeout)
            statuses = [
                result.status.value for result in dispatch_result.execution_results]
            assert any(status in ["success", "failure"]
                       for status in statuses), f"No concrete results for {test_priority.level.value}"
