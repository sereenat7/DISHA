"""
Property-based tests for MCP tool integration framework.

Feature: agentic-disaster-response
Property 8: MCP Tool Selection and Execution
Property 9: Dispatch Resilience
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, strategies as st, settings, Verbosity
from hypothesis.strategies import composite

from agentic_disaster_response.mcp_integration import (
    MCPConfigurationManager, MCPToolSelector, MCPDataFormatter, AlertData, ExecutionStatus
)
from agentic_disaster_response.alert_dispatcher import AlertDispatcher, DispatchResult, RetryConfig
from agentic_disaster_response.models.mcp_tools import (
    MCPToolConfig, MCPToolRegistry, MCPToolType, ToolConfiguration
)
from agentic_disaster_response.models.alert_priority import PriorityLevel, AlertPriority, ResourceType
from agentic_disaster_response.models.context import (
    StructuredContext, GeographicalContext, PopulationData,
    ResourceInventory, RiskMetrics, EvacuationRoute
)
from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
from agentic_disaster_response.models.location import Location


# Hypothesis strategies for generating test data

@composite
def location_strategy(draw):
    """Generate valid Location objects."""
    return Location(
        latitude=draw(st.floats(min_value=-90.0, max_value=90.0)),
        longitude=draw(st.floats(min_value=-180.0, max_value=180.0)),
        address=draw(st.text(min_size=1, max_size=100)),
        administrative_area=draw(st.text(min_size=1, max_size=50)),
        country=draw(st.text(min_size=1, max_size=50))
    )


@composite
def disaster_data_strategy(draw):
    """Generate valid DisasterData objects."""
    return DisasterData(
        disaster_id=draw(st.text(min_size=1, max_size=50)),
        disaster_type=draw(st.sampled_from(DisasterType)),
        location=draw(location_strategy()),
        severity=draw(st.sampled_from(SeverityLevel)),
        timestamp=datetime.now(),
        affected_areas=[],
        estimated_impact=None,
        description=draw(st.text(min_size=1, max_size=200)),
        source="test"
    )


@composite
def alert_priority_strategy(draw):
    """Generate valid AlertPriority objects."""
    return AlertPriority(
        level=draw(st.sampled_from(PriorityLevel)),
        score=draw(st.floats(min_value=0.0, max_value=1.0)),
        reasoning=draw(st.text(min_size=1, max_size=100)),
        estimated_response_time=timedelta(minutes=draw(
            st.integers(min_value=1, max_value=120))),
        required_resources=draw(
            st.lists(st.sampled_from(ResourceType), max_size=5)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0))
    )


@composite
def structured_context_strategy(draw):
    """Generate valid StructuredContext objects."""
    return StructuredContext(
        disaster_info=draw(disaster_data_strategy()),
        geographical_context=GeographicalContext(
            affected_areas=[draw(location_strategy())],
            safe_locations=[draw(location_strategy())]
        ),
        evacuation_routes=[],
        affected_population=PopulationData(
            total_population=draw(st.integers(min_value=1, max_value=100000)),
            vulnerable_population=draw(
                st.integers(min_value=0, max_value=10000))
        ),
        available_resources=ResourceInventory(
            available_shelters=draw(st.integers(min_value=0, max_value=100)),
            shelter_capacity=draw(st.integers(min_value=0, max_value=10000)),
            medical_facilities=draw(st.integers(min_value=0, max_value=50)),
            emergency_vehicles=draw(st.integers(min_value=0, max_value=100)),
            communication_systems=draw(st.integers(min_value=0, max_value=20)),
            backup_power_systems=draw(st.integers(min_value=0, max_value=10))
        ),
        risk_assessment=RiskMetrics(
            overall_risk_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            evacuation_difficulty=draw(
                st.floats(min_value=0.0, max_value=1.0)),
            time_criticality=draw(st.floats(min_value=0.0, max_value=1.0)),
            resource_availability=draw(st.floats(min_value=0.0, max_value=1.0))
        ),
        context_completeness=draw(st.floats(min_value=0.0, max_value=1.0)),
        missing_data_indicators=draw(
            st.lists(st.text(min_size=1, max_size=50), max_size=5))
    )


@composite
def tool_configuration_strategy(draw):
    """Generate valid ToolConfiguration objects."""
    return ToolConfiguration(
        endpoint=f"mcp://{draw(st.text(min_size=1, max_size=20))}",
        timeout_seconds=draw(st.integers(min_value=1, max_value=300)),
        max_retries=draw(st.integers(min_value=0, max_value=5)),
        parameters=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans()),
            max_size=5
        ))
    )


@composite
def mcp_tool_config_strategy(draw):
    """Generate valid MCPToolConfig objects."""
    # Only use tool types that are supported by AlertDispatcher
    supported_tool_types = [MCPToolType.ALERT,
                            MCPToolType.ROUTING, MCPToolType.CONTEXT]
    tool_type = draw(st.sampled_from(supported_tool_types))
    priority_levels = draw(st.lists(st.sampled_from(
        PriorityLevel), min_size=1, max_size=4, unique=True))

    priority_mapping = {}
    for priority in priority_levels:
        priority_mapping[priority] = draw(tool_configuration_strategy())

    return MCPToolConfig(
        tool_name=draw(st.text(min_size=1, max_size=30)),
        tool_type=tool_type,
        priority_mapping=priority_mapping,
        fallback_tools=draw(
            st.lists(st.text(min_size=1, max_size=30), max_size=3)),
        enabled=draw(st.booleans()),
        description=draw(st.text(min_size=1, max_size=100))
    )


class TestMCPToolSelection:
    """Test MCP tool selection logic."""

    @given(
        tool_configs=st.lists(mcp_tool_config_strategy(),
                              min_size=1, max_size=10),
        priority=st.sampled_from(PriorityLevel)
    )
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    def test_property_8_tool_selection_consistency(self, tool_configs: List[MCPToolConfig],
                                                   priority: PriorityLevel):
        """
        **Feature: agentic-disaster-response, Property 8: MCP Tool Selection and Execution**

        For any determined alert priority, the Alert Dispatcher should select appropriate MCP tools,
        format alert data according to tool requirements, and execute with proper error handling.
        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        # Create registry and add tools
        registry = MCPToolRegistry()
        for tool_config in tool_configs:
            registry.register_tool(tool_config)

        selector = MCPToolSelector(registry)

        # Test tool selection
        selected_tools = selector.select_tools_for_priority(priority)

        # Property: All selected tools must support the requested priority
        for tool in selected_tools:
            assert tool.has_priority_support(priority), \
                f"Selected tool {tool.tool_name} does not support priority {priority.value}"

        # Property: All selected tools must be enabled
        for tool in selected_tools:
            assert tool.enabled, f"Selected tool {tool.tool_name} is not enabled"

        # Property: If enabled tools exist that support the priority, at least one should be selected
        enabled_supporting_tools = [
            tool for tool in tool_configs
            if tool.enabled and tool.has_priority_support(priority)
        ]
        if enabled_supporting_tools:
            assert len(selected_tools) > 0, \
                f"No tools selected despite {len(enabled_supporting_tools)} available tools"

    @given(
        tool_configs=st.lists(mcp_tool_config_strategy(),
                              min_size=2, max_size=5),
        priority=st.sampled_from(PriorityLevel)
    )
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    def test_property_8_data_formatting_consistency(self, tool_configs: List[MCPToolConfig],
                                                    priority: PriorityLevel):
        """
        **Feature: agentic-disaster-response, Property 8: MCP Tool Selection and Execution**

        For any alert data and tool configuration, the data formatter should produce
        valid formatted data that includes all required fields.
        **Validates: Requirements 4.2**
        """
        formatter = MCPDataFormatter()

        # Create sample alert data
        alert_data = AlertData(
            alert_id="test-alert-123",
            priority=AlertPriority(
                level=priority,
                score=0.8,
                reasoning="Test reasoning",
                estimated_response_time=timedelta(minutes=15),
                required_resources=[ResourceType.MEDICAL]
            ),
            context=StructuredContext(
                disaster_info=DisasterData(
                    disaster_id="test-disaster",
                    disaster_type=DisasterType.FIRE,
                    location=Location(
                        19.0760, 72.8777, "Test Location", "Test Area", "Test Country"),
                    severity=SeverityLevel.HIGH,
                    timestamp=datetime.now(),
                    affected_areas=[],
                    estimated_impact=None,
                    description="Test disaster",
                    source="test"
                ),
                geographical_context=GeographicalContext(
                    affected_areas=[], safe_locations=[]),
                evacuation_routes=[],
                affected_population=PopulationData(
                    total_population=1000, vulnerable_population=100),
                available_resources=ResourceInventory(
                    available_shelters=5, shelter_capacity=500, medical_facilities=2,
                    emergency_vehicles=10, communication_systems=3, backup_power_systems=2
                ),
                risk_assessment=RiskMetrics(
                    overall_risk_score=0.7, evacuation_difficulty=0.6,
                    time_criticality=0.8, resource_availability=0.5
                ),
                context_completeness=0.9
            ),
            message="Test alert message"
        )

        for tool_config in tool_configs:
            if not tool_config.has_priority_support(priority):
                continue

            try:
                formatted_data = formatter.format_for_tool(
                    alert_data, tool_config, priority)

                # Property: Formatted data must be a dictionary
                assert isinstance(formatted_data, dict), \
                    f"Formatted data for {tool_config.tool_name} is not a dictionary"

                # Property: Formatted data must contain essential fields
                required_fields = ["alert_id", "priority",
                                   "message", "timestamp", "location"]
                for field in required_fields:
                    assert field in formatted_data, \
                        f"Required field '{field}' missing from formatted data for {tool_config.tool_name}"

                # Property: Priority value must match the requested priority
                assert formatted_data["priority"] == priority.value, \
                    f"Priority mismatch in formatted data for {tool_config.tool_name}"

                # Property: Location must contain latitude and longitude
                location_data = formatted_data["location"]
                assert "latitude" in location_data and "longitude" in location_data, \
                    f"Location data incomplete for {tool_config.tool_name}"

            except Exception as e:
                # If tool doesn't support the priority, that's acceptable
                if "No configuration found" in str(e):
                    continue
                else:
                    raise


class TestAlertDispatcher:
    """Test Alert Dispatcher functionality."""

    @given(
        priority=alert_priority_strategy(),
        context=structured_context_strategy(),
        message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    @pytest.mark.asyncio
    async def test_property_9_dispatch_resilience_basic(self, priority: AlertPriority,
                                                        context: StructuredContext,
                                                        message: str):
        """
        **Feature: agentic-disaster-response, Property 9: Dispatch Resilience**

        For any MCP tool execution failure, the Alert Dispatcher should retry with alternative tools
        or escalate the failure, then log completion status and any failures.
        **Validates: Requirements 4.4, 4.5**
        """
        # Create configuration manager with default tools
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()
        registry = config_manager.get_registry()

        # Create dispatcher with retry configuration
        # Fast retries for testing
        retry_config = RetryConfig(max_retries=2, base_delay_seconds=0.01)
        dispatcher = AlertDispatcher(registry, retry_config)

        # Mock the tool execution to simulate various scenarios
        with patch.object(dispatcher, '_mock_tool_execution') as mock_execution:
            # Configure mock to simulate some failures and some successes
            mock_execution.side_effect = self._create_mock_execution_side_effect()

            # Execute dispatch
            result = await dispatcher.dispatch_alerts(
                priority=priority,
                context=context,
                message=message,
                recipients=["test@example.com"],
                channels=["email", "sms"]
            )

            # Property: Dispatch result must be returned
            assert isinstance(
                result, DispatchResult), "Dispatch must return a DispatchResult"

            # Property: Total tools attempted must be non-negative
            assert result.total_tools_attempted >= 0, \
                "Total tools attempted must be non-negative"

            # Property: Successful + failed dispatches should equal total attempts
            assert result.successful_dispatches + result.failed_dispatches == result.total_tools_attempted, \
                "Sum of successful and failed dispatches must equal total attempts"

            # Property: If tools are available, at least one attempt should be made
            available_tools = registry.get_enabled_tools()
            supporting_tools = [tool for tool in available_tools
                                if tool.has_priority_support(priority.level)]
            if supporting_tools:
                assert result.total_tools_attempted > 0, \
                    "At least one tool should be attempted when tools are available"

            # Property: Execution results list length should match total attempts
            assert len(result.execution_results) == result.total_tools_attempted, \
                "Execution results count must match total attempts"

            # Property: Total execution time should be non-negative
            assert result.total_execution_time_ms >= 0, \
                "Total execution time must be non-negative"

    def _create_mock_execution_side_effect(self):
        """Create a side effect function for mock tool execution."""
        from agentic_disaster_response.mcp_integration import ExecutionResult, ExecutionStatus

        def side_effect(tool_config, tool_configuration, formatted_data):
            # Simulate different outcomes based on tool name
            if "backup" in tool_config.tool_name:
                # Backup tools have mixed success
                import random
                if random.random() > 0.5:
                    return ExecutionResult(
                        status=ExecutionStatus.SUCCESS,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=100,
                        response_data={"status": "success"}
                    )
                else:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILURE,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=50,
                        error_message="Backup tool failure"
                    )
            else:
                # Primary tools mostly succeed
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    tool_name=tool_config.tool_name,
                    execution_time_ms=80,
                    response_data={"status": "success"}
                )

        return side_effect

    @given(
        tool_configs=st.lists(mcp_tool_config_strategy(),
                              min_size=1, max_size=5),
        priority=st.sampled_from(PriorityLevel)
    )
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    @pytest.mark.asyncio
    async def test_property_9_fallback_mechanism(self, tool_configs: List[MCPToolConfig],
                                                 priority: PriorityLevel):
        """
        **Feature: agentic-disaster-response, Property 9: Dispatch Resilience**

        For any primary tool failure, the system should attempt fallback tools
        and track fallback usage appropriately.
        **Validates: Requirements 4.4, 4.5**
        """
        # Create registry with tools that have fallbacks
        registry = MCPToolRegistry()

        # Ensure at least one tool supports the priority and has fallbacks
        if tool_configs:
            primary_tool = tool_configs[0]
            # Ensure it supports the priority and is enabled
            primary_tool.enabled = True  # Force enable for testing
            if priority not in primary_tool.priority_mapping:
                primary_tool.priority_mapping[priority] = ToolConfiguration(
                    endpoint=f"mcp://test/{priority.value}",
                    timeout_seconds=30,
                    max_retries=1
                )

            # Add fallback tools
            fallback_tool_names = [
                f"fallback_{i}" for i in range(min(2, len(tool_configs)))]
            primary_tool.fallback_tools = fallback_tool_names

            registry.register_tool(primary_tool)

            # Register fallback tools
            for i, fallback_name in enumerate(fallback_tool_names):
                if i + 1 < len(tool_configs):
                    fallback_tool = tool_configs[i + 1]
                    fallback_tool.tool_name = fallback_name
                    fallback_tool.enabled = True  # Force enable for testing
                    if priority not in fallback_tool.priority_mapping:
                        fallback_tool.priority_mapping[priority] = ToolConfiguration(
                            endpoint=f"mcp://fallback/{priority.value}",
                            timeout_seconds=30,
                            max_retries=1
                        )
                    registry.register_tool(fallback_tool)

        # Create dispatcher
        dispatcher = AlertDispatcher(registry)

        # Create test context and alert data
        context = StructuredContext(
            disaster_info=DisasterData(
                disaster_id="test",
                disaster_type=DisasterType.FIRE,
                location=Location(0.0, 0.0, "Test", "Test", "Test"),
                severity=SeverityLevel.HIGH,
                timestamp=datetime.now(),
                affected_areas=[],
                estimated_impact=None,
                description="Test",
                source="test"
            ),
            geographical_context=GeographicalContext(
                affected_areas=[], safe_locations=[]),
            evacuation_routes=[],
            affected_population=PopulationData(
                total_population=100, vulnerable_population=10),
            available_resources=ResourceInventory(
                available_shelters=1, shelter_capacity=100, medical_facilities=1,
                emergency_vehicles=1, communication_systems=1, backup_power_systems=1
            ),
            risk_assessment=RiskMetrics(
                overall_risk_score=0.5, evacuation_difficulty=0.5,
                time_criticality=0.5, resource_availability=0.5
            ),
            context_completeness=1.0
        )

        alert_priority = AlertPriority(
            level=priority,
            score=0.7,
            reasoning="Test",
            estimated_response_time=timedelta(minutes=10),
            required_resources=[]
        )

        # Mock tool execution to force primary tool failure
        with patch.object(dispatcher, '_mock_tool_execution') as mock_execution:
            def failing_primary_success_fallback(tool_config, tool_configuration, formatted_data):
                from agentic_disaster_response.mcp_integration import ExecutionResult, ExecutionStatus

                if "fallback" in tool_config.tool_name:
                    return ExecutionResult(
                        status=ExecutionStatus.SUCCESS,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=100,
                        response_data={"status": "fallback_success"}
                    )
                else:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILURE,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=50,
                        error_message="Primary tool forced failure"
                    )

            mock_execution.side_effect = failing_primary_success_fallback

            # Execute dispatch
            result = await dispatcher.dispatch_alerts(
                priority=alert_priority,
                context=context,
                message="Test message"
            )

            # Property: If fallback tools exist and primary fails, fallback should be attempted
            if registry.tools:
                primary_tools = [tool for tool in registry.tools.values()
                                 if not tool.tool_name.startswith("fallback")]
                fallback_tools = [tool for tool in registry.tools.values()
                                  if tool.tool_name.startswith("fallback")]

                # Only check assertions if we have enabled tools that support the priority
                enabled_primary_tools = [tool for tool in primary_tools
                                         if tool.enabled and tool.has_priority_support(priority)]
                enabled_fallback_tools = [tool for tool in fallback_tools
                                          if tool.enabled and tool.has_priority_support(priority)]

                if enabled_primary_tools:
                    # Property: If enabled primary tools exist, at least one attempt should be made
                    assert result.total_tools_attempted >= len(enabled_primary_tools), \
                        f"Total attempts ({result.total_tools_attempted}) should include at least primary tools ({len(enabled_primary_tools)})"

                    # Property: If fallbacks were used, the flag should be set
                    if result.fallback_used and enabled_fallback_tools:
                        assert result.successful_dispatches > 0, \
                            "If fallback was used, there should be successful dispatches"


class TestMCPConfigurationManager:
    """Test MCP configuration management."""

    def test_default_configuration_loading(self):
        """Test that default configurations are loaded correctly."""
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()
        registry = config_manager.get_registry()

        # Property: Default tools should be registered
        tools = registry.get_enabled_tools()
        assert len(tools) > 0, "Default configuration should register tools"

        # Property: Each tool type should have at least one tool
        tool_types = {tool.tool_type for tool in tools}
        expected_types = {MCPToolType.ALERT,
                          MCPToolType.ROUTING, MCPToolType.CONTEXT}
        assert expected_types.issubset(tool_types), \
            "Default configuration should include alert, routing, and context tools"

        # Property: All tools should have priority mappings
        for tool in tools:
            assert len(tool.priority_mapping) > 0, \
                f"Tool {tool.tool_name} should have priority mappings"

    def test_configuration_validation(self):
        """Test configuration validation."""
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()

        # Property: Valid configurations should pass validation
        errors = config_manager.validate_all_configurations()
        assert len(
            errors) == 0, f"Default configurations should be valid, but found errors: {errors}"
