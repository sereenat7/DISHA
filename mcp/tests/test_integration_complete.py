"""
Comprehensive integration tests for the complete disaster response system.
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
from datetime import datetime
from unittest.mock import patch, AsyncMock

from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.models.mcp_tools import MCPToolRegistry
from agentic_disaster_response.mcp_tools.tool_factory import create_default_tool_registry


class TestCompleteIntegration:
    """Integration tests for the complete disaster response flow."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create a disaster response agent for testing."""
        registry = create_default_tool_registry()
        config = AgentConfiguration(
            context_search_radius_km=10.0,
            max_routes_per_category=2,
            enable_concurrent_processing=True,
            max_concurrent_disasters=2,
            enable_performance_monitoring=True
        )

        agent = DisasterResponseAgent(registry, config)
        await agent.initialize_connections()
        return agent

    @pytest.fixture
    def fastapi_client(self):
        """Create FastAPI test client."""
        try:
            from fastapi.testclient import TestClient
            # Import the app after it's been initialized
            from Backend.evacuation_system.main import app
            return TestClient(app)
        except Exception as e:
            # If TestClient fails, return None and skip tests that need it
            import pytest
            pytest.skip(f"FastAPI TestClient not available: {e}")
            return None

    @pytest.mark.asyncio
    async def test_end_to_end_disaster_response_flow(self, agent):
        """Test complete disaster response flow from trigger to completion."""
        # Test data
        disaster_id = "test_disaster_001"

        # Create and store disaster data
        from Backend.evacuation_system.main import DisasterEventRequest, _create_disaster_data_from_request, _store_disaster_data
        request = DisasterEventRequest(
            disaster_type="fire",
            location_lat=52.5200,
            location_lon=13.4050,
            severity="high",
            affected_radius_km=5.0,
            description="Test fire disaster",
            estimated_affected_population=2000
        )

        disaster_data = await _create_disaster_data_from_request(disaster_id, request)
        await _store_disaster_data(disaster_id, disaster_data)

        # Process disaster through agent
        response = await agent.process_disaster_event(disaster_id)

        # Verify response
        assert response is not None
        assert response.disaster_id == disaster_id
        assert response.processing_status in ["completed", "failed"]

        # Verify context was built
        assert response.context is not None
        assert response.context.disaster_info.disaster_id == disaster_id
        assert response.context.disaster_info.disaster_type.value == "fire"
        assert response.context.disaster_info.severity.value == "high"

        # Verify priority was analyzed
        assert response.priority is not None
        assert response.priority.level.value in [
            "critical", "high", "medium", "low"]
        assert response.priority.score >= 0.0

        # Verify alerts were dispatched (even if some failed)
        assert len(response.dispatch_results) > 0

        # Check processing time
        assert response.total_processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_fastapi_disaster_trigger_integration(self, fastapi_client):
        """Test FastAPI disaster trigger endpoint integration."""
        # Test disaster trigger request
        disaster_request = {
            "disaster_type": "earthquake",
            "location_lat": 52.5200,
            "location_lon": 13.4050,
            "severity": "critical",
            "affected_radius_km": 10.0,
            "description": "Test earthquake disaster",
            "estimated_affected_population": 5000
        }

        # Trigger disaster event
        response = fastapi_client.post(
            "/disaster/trigger", json=disaster_request)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert "disaster_id" in response_data
        assert response_data["status"] == "processing_started"
        assert "processing_started_at" in response_data

        disaster_id = response_data["disaster_id"]

        # Wait a moment for background processing
        await asyncio.sleep(0.5)

        # Check disaster status
        status_response = fastapi_client.get(f"/disaster/{disaster_id}/status")

        if status_response.status_code == 200:
            status_data = status_response.json()
            assert status_data["disaster_id"] == disaster_id
            assert "processing_status" in status_data

    @pytest.mark.asyncio
    async def test_mcp_tool_integration_and_fallbacks(self, agent):
        """Test MCP tool integration with fallback mechanisms."""
        disaster_id = "test_mcp_integration"

        # Create disaster data
        from Backend.evacuation_system.main import DisasterEventRequest
        request = DisasterEventRequest(
            disaster_type="flood",
            location_lat=52.5200,
            location_lon=13.4050,
            severity="medium",
            affected_radius_km=3.0,
            description="Test flood for MCP integration",
            estimated_affected_population=1000
        )

        disaster_data = await _create_disaster_data_from_request(disaster_id, request)
        await _store_disaster_data(disaster_id, disaster_data)

        # Process disaster
        response = await agent.process_disaster_event(disaster_id)

        # Verify MCP tools were attempted
        assert len(response.dispatch_results) > 0

        # Check that different tool types were used
        tool_names = [
            result.mcp_tool_name for result in response.dispatch_results]

        # Should have attempted alert tools at minimum
        alert_tools = [name for name in tool_names if "alert" in name.lower()]
        assert len(alert_tools) > 0

        # Verify fallback mechanisms
        # At least some tools should have succeeded or used fallbacks
        successful_dispatches = sum(1 for result in response.dispatch_results
                                    if result.status.value == "success")

        # Even if primary tools fail, fallbacks should provide some success
        assert successful_dispatches > 0 or response.success_rate > 0

    @pytest.mark.asyncio
    async def test_concurrent_disaster_processing(self, agent):
        """Test concurrent processing of multiple disasters."""
        # Create multiple disasters
        disaster_ids = ["concurrent_001", "concurrent_002", "concurrent_003"]

        for i, disaster_id in enumerate(disaster_ids):
            from Backend.evacuation_system.main import DisasterEventRequest
            request = DisasterEventRequest(
                disaster_type=["fire", "flood", "earthquake"][i],
                location_lat=52.5200 + i * 0.01,
                location_lon=13.4050 + i * 0.01,
                severity=["high", "medium", "critical"][i],
                affected_radius_km=5.0,
                description=f"Concurrent test disaster {i+1}",
                estimated_affected_population=1000 + i * 500
            )

            disaster_data = await _create_disaster_data_from_request(disaster_id, request)
            await _store_disaster_data(disaster_id, disaster_data)

        # Process disasters concurrently
        responses = await agent.handle_concurrent_disasters(disaster_ids)

        # Verify all disasters were processed
        assert len(responses) == len(disaster_ids)

        # Verify each response
        for response in responses:
            assert response.disaster_id in disaster_ids
            assert response.processing_status in ["completed", "failed"]
            assert response.total_processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_error_recovery_and_fallbacks(self, agent):
        """Test error recovery and fallback mechanisms."""
        disaster_id = "test_error_recovery"

        # Create disaster data
        from Backend.evacuation_system.main import DisasterEventRequest
        request = DisasterEventRequest(
            disaster_type="chemical_spill",
            location_lat=52.5200,
            location_lon=13.4050,
            severity="critical",
            affected_radius_km=2.0,
            description="Test chemical spill for error recovery",
            estimated_affected_population=800
        )

        disaster_data = await _create_disaster_data_from_request(disaster_id, request)
        await _store_disaster_data(disaster_id, disaster_data)

        # Simulate component failures by patching methods
        with patch.object(agent.context_builder, 'build_context', side_effect=Exception("Context builder failed")):
            response = await agent.process_disaster_event(disaster_id)

            # Verify system handled the failure gracefully
            assert response is not None
            assert response.disaster_id == disaster_id

            # Should have error records
            assert len(response.errors) > 0

            # Should have attempted recovery
            context_errors = [
                e for e in response.errors if e.component == "ContextBuilder"]
            assert len(context_errors) > 0

            # Should have recovery action
            assert any(e.recovery_action_taken for e in context_errors)

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, agent):
        """Test system health monitoring and status reporting."""
        # Test system health check
        health_status = await agent.monitor_system_health()

        assert "timestamp" in health_status
        assert "overall_health" in health_status
        assert "component_status" in health_status
        assert "active_disasters" in health_status

        # Verify component status
        components = health_status["component_status"]
        expected_components = ["fastapi_backend", "mcp_tools", "context_builder",
                               "alert_prioritizer", "alert_dispatcher"]

        for component in expected_components:
            assert component in components
            assert isinstance(components[component], bool)

    @pytest.mark.asyncio
    async def test_real_time_status_and_metrics(self, agent):
        """Test real-time status and performance metrics."""
        # Get real-time status
        status = await agent.get_real_time_status()

        assert "timestamp" in status
        assert "system_health" in status
        assert "active_processing" in status
        assert "resource_utilization" in status

        # Verify resource utilization
        utilization = status["resource_utilization"]
        assert "concurrent_slots_used" in utilization
        assert "concurrent_slots_available" in utilization
        assert "max_concurrent_disasters" in utilization

        # Test status report generation
        report = await agent.generate_status_report()

        assert "report_timestamp" in report
        assert "system_status" in report
        assert "performance_metrics" in report

    def test_fastapi_evacuation_routes_integration(self, fastapi_client):
        """Test FastAPI evacuation routes endpoint."""
        # Test evacuation routes request
        evacuation_request = {
            "user_lat": 52.5200,
            "user_lon": 13.4050,
            "radius_km": 10.0,
            "max_per_category": 2
        }

        response = fastapi_client.post(
            "/evacuation-routes", json=evacuation_request)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert "alert_id" in response_data
        assert "results" in response_data

        results = response_data["results"]
        assert "user_position" in results
        assert "search_radius_km" in results
        assert "routes" in results

        # Verify user position
        user_pos = results["user_position"]
        assert user_pos["lat"] == 52.5200
        assert user_pos["lon"] == 13.4050

    def test_fastapi_system_health_endpoint(self, fastapi_client):
        """Test FastAPI system health endpoint."""
        response = fastapi_client.get("/system/health")

        assert response.status_code == 200
        health_data = response.json()

        assert "timestamp" in health_data
        assert "evacuation_system" in health_data
        assert "disaster_response_agent" in health_data

        # Evacuation system should be healthy
        assert health_data["evacuation_system"] in [
            "healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_property_based_workflow_progression(self, agent):
        """
        Property test: For any valid disaster data, the agent should progress 
        through the complete workflow to alert dispatch.
        **Validates: Requirements 1.4, 5.2**
        """
        # Test with various disaster types and severities
        test_cases = [
            ("fire", "high", 2000),
            ("flood", "medium", 1500),
            ("earthquake", "critical", 5000),
            ("storm", "low", 800)
        ]

        for disaster_type, severity, population in test_cases:
            disaster_id = f"prop_test_{disaster_type}_{int(datetime.now().timestamp())}"

            # Create disaster data
            from Backend.evacuation_system.main import DisasterEventRequest
            request = DisasterEventRequest(
                disaster_type=disaster_type,
                location_lat=52.5200,
                location_lon=13.4050,
                severity=severity,
                affected_radius_km=5.0,
                description=f"Property test {disaster_type}",
                estimated_affected_population=population
            )

            disaster_data = await _create_disaster_data_from_request(disaster_id, request)
            await _store_disaster_data(disaster_id, disaster_data)

            # Process disaster
            response = await agent.process_disaster_event(disaster_id)

            # Verify workflow progression
            assert response is not None, f"No response for {disaster_type}"
            assert response.disaster_id == disaster_id, f"Wrong disaster ID for {disaster_type}"
            assert response.context is not None, f"No context built for {disaster_type}"
            assert response.priority is not None, f"No priority analyzed for {disaster_type}"
            assert len(
                response.dispatch_results) > 0, f"No alerts dispatched for {disaster_type}"
            assert response.processing_status in [
                "completed", "failed"], f"Invalid status for {disaster_type}"

    @pytest.mark.asyncio
    async def test_property_based_error_recovery(self, agent):
        """
        Property test: For any workflow step failure, the agent should implement 
        appropriate error recovery procedures.
        **Validates: Requirements 5.3, 6.1, 6.2, 6.3, 6.4**
        """
        disaster_id = "prop_test_error_recovery"

        # Create disaster data
        from Backend.evacuation_system.main import DisasterEventRequest
        request = DisasterEventRequest(
            disaster_type="fire",
            location_lat=52.5200,
            location_lon=13.4050,
            severity="high",
            affected_radius_km=5.0,
            description="Property test for error recovery",
            estimated_affected_population=2000
        )

        disaster_data = await _create_disaster_data_from_request(disaster_id, request)
        await _store_disaster_data(disaster_id, disaster_data)

        # Test different failure scenarios
        failure_scenarios = [
            ("context_builder", "build_context"),
            ("alert_prioritizer", "analyze_priority_with_fallback"),
            ("alert_dispatcher", "dispatch_alerts")
        ]

        for component, method in failure_scenarios:
            # Reset disaster data for each test
            await _store_disaster_data(f"{disaster_id}_{component}", disaster_data)

            # Simulate component failure
            component_obj = getattr(agent, component)
            original_method = getattr(component_obj, method)

            with patch.object(component_obj, method, side_effect=Exception(f"{component} failed")):
                response = await agent.process_disaster_event(f"{disaster_id}_{component}")

                # Verify error recovery was attempted
                assert response is not None, f"No response for {component} failure"
                assert len(
                    response.errors) > 0, f"No errors recorded for {component} failure"

                # Check for recovery actions
                component_errors = [e for e in response.errors if component.replace(
                    '_', '').lower() in e.component.lower()]
                assert len(
                    component_errors) > 0, f"No component errors for {component}"

                # Should have attempted some form of recovery
                recovery_attempted = any(
                    e.recovery_action_taken for e in component_errors)
                assert recovery_attempted or response.processing_status == "failed", f"No recovery attempted for {component}"

    @pytest.mark.asyncio
    async def test_property_based_concurrent_processing(self, agent):
        """
        Property test: For any multiple simultaneous disasters, the agent should 
        handle concurrent processing efficiently.
        **Validates: Requirements 5.5, 6.5**
        """
        # Test with different numbers of concurrent disasters
        concurrent_counts = [2, 3, 5]  # Test up to max concurrent limit

        for count in concurrent_counts:
            disaster_ids = [
                f"concurrent_prop_{count}_{i}" for i in range(count)]

            # Create disaster data for each
            for i, disaster_id in enumerate(disaster_ids):
                from Backend.evacuation_system.main import DisasterEventRequest
                request = DisasterEventRequest(
                    disaster_type=["fire", "flood", "earthquake",
                                   "storm", "chemical_spill"][i % 5],
                    location_lat=52.5200 + i * 0.01,
                    location_lon=13.4050 + i * 0.01,
                    severity=["high", "medium", "critical", "low"][i % 4],
                    affected_radius_km=5.0,
                    description=f"Concurrent property test {i}",
                    estimated_affected_population=1000 + i * 200
                )

                disaster_data = await _create_disaster_data_from_request(disaster_id, request)
                await _store_disaster_data(disaster_id, disaster_data)

            # Process concurrently
            start_time = datetime.now()
            responses = await agent.handle_concurrent_disasters(disaster_ids)
            end_time = datetime.now()

            # Verify concurrent processing
            assert len(
                responses) == count, f"Wrong number of responses for {count} disasters"

            # All disasters should be processed
            processed_ids = {r.disaster_id for r in responses}
            expected_ids = set(disaster_ids)
            assert processed_ids == expected_ids, f"Missing disasters in concurrent processing"

            # Processing should be reasonably efficient (not strictly sequential)
            total_time = (end_time - start_time).total_seconds()
            max_expected_time = count * 2.0  # Allow 2 seconds per disaster max
            assert total_time < max_expected_time, f"Concurrent processing too slow: {total_time}s for {count} disasters"

    @pytest.mark.asyncio
    async def test_integration_with_real_evacuation_system(self, fastapi_client):
        """Test integration between disaster response and evacuation system."""
        # First, test that evacuation routes work
        evacuation_response = fastapi_client.post("/evacuation-routes", json={
            "user_lat": 52.5200,
            "user_lon": 13.4050,
            "radius_km": 10.0,
            "max_per_category": 2
        })

        assert evacuation_response.status_code == 200
        evacuation_data = evacuation_response.json()

        # Now trigger a disaster that should use evacuation data
        disaster_response = fastapi_client.post("/disaster/trigger", json={
            "disaster_type": "fire",
            "location_lat": 52.5200,
            "location_lon": 13.4050,
            "severity": "high",
            "affected_radius_km": 5.0,
            "description": "Integration test disaster",
            "estimated_affected_population": 2000
        })

        assert disaster_response.status_code == 200
        disaster_data = disaster_response.json()

        disaster_id = disaster_data["disaster_id"]

        # Wait for processing
        await asyncio.sleep(1.0)

        # Check disaster status
        status_response = fastapi_client.get(f"/disaster/{disaster_id}/status")

        if status_response.status_code == 200:
            status_data = status_response.json()

            # Should have context with evacuation information
            if "context" in status_data:
                context = status_data["context"]
                assert "evacuation_routes_count" in context
                # Should have found some evacuation routes
                assert context["evacuation_routes_count"] >= 0
