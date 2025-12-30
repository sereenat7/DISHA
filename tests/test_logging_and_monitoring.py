"""
Property-based tests for comprehensive logging and monitoring functionality.

Tests Properties 13 and 14 from the design document:
- Property 13: Comprehensive Logging
- Property 14: Status Reporting

Validates Requirements 7.1, 7.2, 7.3, 5.4, 7.4, 7.5
"""

import pytest
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from hypothesis import given, strategies as st, settings, Verbosity

from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.core.workflow_logger import WorkflowLogger, WorkflowStep, ActionType
from agentic_disaster_response.core.logging_config import setup_logging, get_logger
from agentic_disaster_response.models.mcp_tools import MCPToolRegistry
from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.alert_priority import AlertPriority, PriorityLevel


class LogCapture:
    """Helper class to capture log messages for testing."""

    def __init__(self):
        self.log_records = []
        self.handler = None

    def __enter__(self):
        self.handler = logging.Handler()
        self.handler.emit = self.capture_log

        # Add handler to all relevant loggers
        loggers = [
            logging.getLogger('agentic_disaster_response'),
            logging.getLogger('agentic_disaster_response.workflow'),
            logging.getLogger(
                'agentic_disaster_response.disaster_response_agent')
        ]

        for logger in loggers:
            logger.addHandler(self.handler)
            logger.setLevel(logging.DEBUG)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove handler from all loggers
        loggers = [
            logging.getLogger('agentic_disaster_response'),
            logging.getLogger('agentic_disaster_response.workflow'),
            logging.getLogger(
                'agentic_disaster_response.disaster_response_agent')
        ]

        for logger in loggers:
            if self.handler in logger.handlers:
                logger.removeHandler(self.handler)

    def capture_log(self, record):
        """Capture log record."""
        self.log_records.append(record)

    def get_messages(self) -> List[str]:
        """Get all captured log messages."""
        return [record.getMessage() for record in self.log_records]

    def get_records_with_extra(self, extra_key: str) -> List[logging.LogRecord]:
        """Get log records that contain specific extra data."""
        return [record for record in self.log_records if hasattr(record, extra_key)]

    def get_workflow_entries(self) -> List[Dict[str, Any]]:
        """Get workflow log entries."""
        entries = []
        for record in self.log_records:
            if hasattr(record, 'workflow_entry'):
                entries.append(record.workflow_entry)
        return entries

    def get_error_entries(self) -> List[Dict[str, Any]]:
        """Get error log entries."""
        entries = []
        for record in self.log_records:
            if hasattr(record, 'error_entry'):
                entries.append(record.error_entry)
        return entries

    def get_dispatch_entries(self) -> List[Dict[str, Any]]:
        """Get dispatch log entries."""
        entries = []
        for record in self.log_records:
            if hasattr(record, 'dispatch_entry'):
                entries.append(record.dispatch_entry)
        return entries


# Hypothesis strategies for generating test data
@st.composite
def disaster_data_strategy(draw):
    """Generate random disaster data for testing."""
    disaster_id = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    disaster_type = draw(st.sampled_from(list(DisasterType)))
    severity = draw(st.sampled_from(list(SeverityLevel)))

    location = Location(
        latitude=draw(st.floats(min_value=-90, max_value=90)),
        longitude=draw(st.floats(min_value=-180, max_value=180)),
        address=draw(st.text(min_size=10, max_size=50)),
        administrative_area=draw(st.text(min_size=5, max_size=20))
    )

    return {
        'disaster_id': disaster_id,
        'disaster_type': disaster_type,
        'location': location,
        'severity': severity
    }


@st.composite
def workflow_step_strategy(draw):
    """Generate random workflow steps for testing."""
    return draw(st.sampled_from(list(WorkflowStep)))


@st.composite
def action_type_strategy(draw):
    """Generate random action types for testing."""
    return draw(st.sampled_from(list(ActionType)))


class TestComprehensiveLogging:
    """
    Test Property 13: Comprehensive Logging

    **Feature: agentic-disaster-response, Property 13: Comprehensive Logging**
    **Validates: Requirements 7.1, 7.2, 7.3**
    """

    @given(disaster_data_strategy())
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    def test_workflow_step_logging_completeness(self, disaster_data):
        """
        Property 13a: For any workflow execution, all actions should be logged with timestamps.

        **Feature: agentic-disaster-response, Property 13: Comprehensive Logging**
        **Validates: Requirements 7.1**
        """
        disaster_id = disaster_data['disaster_id']

        with LogCapture() as log_capture:
            # Create workflow logger
            workflow_logger = WorkflowLogger(disaster_id, "TestComponent")

            # Log workflow start
            workflow_logger.log_workflow_start({"test": "data"})

            # Log various workflow steps
            workflow_logger.log_step_start(WorkflowStep.DATA_RETRIEVAL)
            workflow_logger.log_step_progress(
                WorkflowStep.DATA_RETRIEVAL, "Retrieving data")
            workflow_logger.log_step_success(
                WorkflowStep.DATA_RETRIEVAL, "Data retrieved successfully")

            workflow_logger.log_step_start(WorkflowStep.CONTEXT_BUILDING)
            workflow_logger.log_step_success(
                WorkflowStep.CONTEXT_BUILDING, "Context built")

            workflow_logger.log_workflow_completion(True, {"success": True})

            # Verify all workflow steps are logged
            workflow_entries = log_capture.get_workflow_entries()

            # Should have entries for: start, data_retrieval (start, progress, success), context_building (start, success), completion
            assert len(
                workflow_entries) >= 6, f"Expected at least 6 workflow entries, got {len(workflow_entries)}"

            # Verify all entries have timestamps
            for entry in workflow_entries:
                assert 'timestamp' in entry, "Workflow entry missing timestamp"
                assert entry['disaster_id'] == disaster_id, "Disaster ID mismatch in workflow entry"
                assert 'component' in entry, "Workflow entry missing component"
                assert 'message' in entry, "Workflow entry missing message"

            # Verify workflow progression is logged
            step_types = [entry['workflow_step'].value if hasattr(
                entry['workflow_step'], 'value') else entry['workflow_step'] for entry in workflow_entries]
            assert 'initialization' in step_types, "Initialization step not logged"
            assert 'data_retrieval' in step_types, "Data retrieval step not logged"
            assert 'context_building' in step_types, "Context building step not logged"
            assert 'completion' in step_types, "Completion step not logged"

    @given(disaster_data_strategy(), st.text(min_size=10, max_size=100))
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    def test_error_logging_with_recovery_context(self, disaster_data, error_message):
        """
        Property 13b: For any error occurrence, error details with context and recovery actions should be logged.

        **Feature: agentic-disaster-response, Property 13: Comprehensive Logging**
        **Validates: Requirements 7.2**
        """
        disaster_id = disaster_data['disaster_id']

        with LogCapture() as log_capture:
            workflow_logger = WorkflowLogger(disaster_id, "TestComponent")

            # Create test error and context
            test_error = Exception(error_message)
            error_context = {
                "operation": "test_operation",
                "component": "TestComponent",
                "disaster_type": disaster_data['disaster_type'].value,
                "severity": disaster_data['severity'].value
            }
            recovery_action = "Attempting fallback mechanism"

            # Log error with recovery context
            workflow_logger.log_error_with_recovery(
                test_error, error_context, recovery_action, True
            )

            # Verify error logging
            error_entries = log_capture.get_error_entries()
            assert len(error_entries) >= 1, "Error entry not logged"

            error_entry = error_entries[0]
            assert error_entry['disaster_id'] == disaster_id, "Disaster ID mismatch in error entry"
            assert error_entry['error_message'] == error_message, "Error message mismatch"
            assert error_entry['recovery_action'] == recovery_action, "Recovery action not logged"
            assert error_entry['recovery_success'] == True, "Recovery success not logged"
            assert 'timestamp' in error_entry, "Error entry missing timestamp"
            assert 'context' in error_entry, "Error entry missing context"
            assert error_entry['context'] == error_context, "Error context mismatch"

    @given(
        disaster_data_strategy(),
        st.text(min_size=5, max_size=20),  # mcp_tool_name
        st.integers(min_value=1, max_value=10000),  # recipients_count
        st.integers(min_value=0, max_value=10000),  # successful_deliveries
        st.integers(min_value=0, max_value=10000),  # failed_deliveries
        st.lists(st.text(min_size=3, max_size=15),
                 min_size=1, max_size=5)  # delivery_channels
    )
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    def test_alert_dispatch_logging_with_delivery_status(self, disaster_data, mcp_tool_name,
                                                         recipients_count, successful_deliveries,
                                                         failed_deliveries, delivery_channels):
        """
        Property 13c: For any alert dispatch, delivery status and recipient information should be logged.

        **Feature: agentic-disaster-response, Property 13: Comprehensive Logging**
        **Validates: Requirements 7.3**
        """
        disaster_id = disaster_data['disaster_id']

        with LogCapture() as log_capture:
            workflow_logger = WorkflowLogger(disaster_id, "AlertDispatcher")

            dispatch_id = f"{disaster_id}_dispatch_001"

            # Log dispatch attempt
            workflow_logger.log_dispatch_attempt(
                dispatch_id, mcp_tool_name, recipients_count, delivery_channels
            )

            # Log dispatch result
            workflow_logger.log_dispatch_result(
                dispatch_id, mcp_tool_name, recipients_count,
                successful_deliveries, failed_deliveries, delivery_channels,
                execution_time_ms=150.0, retry_count=1
            )

            # Verify dispatch logging
            dispatch_entries = log_capture.get_dispatch_entries()
            assert len(
                dispatch_entries) >= 2, f"Expected at least 2 dispatch entries, got {len(dispatch_entries)}"

            # Debug: Print all entries to understand the structure
            print(f"DEBUG: Found {len(dispatch_entries)} dispatch entries:")
            for i, entry in enumerate(dispatch_entries):
                print(
                    f"  Entry {i}: status={entry.get('status')}, successful={entry.get('successful_deliveries')}, failed={entry.get('failed_deliveries')}")

            # Find attempt and result entries by status
            attempt_entries = [entry for entry in dispatch_entries if entry.get(
                'status') == 'attempting']
            result_entries = [entry for entry in dispatch_entries if entry.get(
                'status') != 'attempting']

            assert len(
                attempt_entries) >= 1, f"Expected at least 1 attempt entry, got {len(attempt_entries)}"
            assert len(
                result_entries) >= 1, f"Expected at least 1 result entry, got {len(result_entries)}"

            # Check dispatch attempt entry (first attempt entry)
            attempt_entry = attempt_entries[0]
            assert attempt_entry['disaster_id'] == disaster_id, "Disaster ID mismatch in dispatch attempt"
            assert attempt_entry['mcp_tool_name'] == mcp_tool_name, "MCP tool name mismatch"
            assert attempt_entry['recipients_count'] == recipients_count, "Recipients count mismatch"
            assert attempt_entry['delivery_channels'] == delivery_channels, "Delivery channels mismatch"
            assert attempt_entry['status'] == "attempting", "Dispatch attempt status mismatch"
            assert attempt_entry['successful_deliveries'] == 0, "Dispatch attempt should have 0 successful deliveries"
            assert attempt_entry['failed_deliveries'] == 0, "Dispatch attempt should have 0 failed deliveries"
            assert 'timestamp' in attempt_entry, "Dispatch attempt missing timestamp"

            # Check dispatch result entry (first result entry)
            result_entry = result_entries[0]
            assert result_entry['disaster_id'] == disaster_id, "Disaster ID mismatch in dispatch result"
            assert result_entry['successful_deliveries'] == successful_deliveries, "Successful deliveries mismatch"
            assert result_entry['failed_deliveries'] == failed_deliveries, "Failed deliveries mismatch"
            assert result_entry['execution_time_ms'] == 150.0, "Execution time mismatch"
            assert result_entry['retry_count'] == 1, "Retry count mismatch"
            assert 'timestamp' in result_entry, "Dispatch result missing timestamp"


class TestStatusReporting:
    """
    Test Property 14: Status Reporting

    **Feature: agentic-disaster-response, Property 14: Status Reporting**
    **Validates: Requirements 5.4, 7.4, 7.5**
    """

    @given(disaster_data_strategy())
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    @pytest.mark.asyncio
    async def test_comprehensive_status_report_generation(self, disaster_data):
        """
        Property 14a: For any completed workflow, comprehensive summary reports should be generated.

        **Feature: agentic-disaster-response, Property 14: Status Reporting**
        **Validates: Requirements 5.4, 7.4**
        """
        # Create mock agent
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_enabled_tools.return_value = []

        config = AgentConfiguration(
            max_concurrent_disasters=3,
            enable_performance_monitoring=True
        )

        mock_agent = DisasterResponseAgent(mock_registry, config)

        disaster_id = disaster_data['disaster_id']

        # Mock some active disasters
        from agentic_disaster_response.models.response import DisasterResponse
        from agentic_disaster_response.models.disaster_data import ProcessingStatus

        mock_response = DisasterResponse(
            disaster_id=disaster_id,
            processing_status=ProcessingStatus.COMPLETED.value
        )
        mock_response.mark_completed()

        mock_agent.active_disasters[disaster_id] = mock_response

        # Generate status report
        status_report = await mock_agent.generate_status_report(disaster_id)

        # Verify comprehensive status report structure
        assert 'report_timestamp' in status_report, "Status report missing timestamp"
        assert 'system_status' in status_report, "Status report missing system status"
        assert 'disaster_summaries' in status_report, "Status report missing disaster summaries"
        assert 'performance_metrics' in status_report, "Status report missing performance metrics"
        assert 'error_summary' in status_report, "Status report missing error summary"

        # Verify disaster summary completeness
        disaster_summaries = status_report['disaster_summaries']
        assert len(disaster_summaries) >= 1, "No disaster summaries in report"

        summary = disaster_summaries[0]
        assert summary['disaster_id'] == disaster_id, "Disaster ID mismatch in summary"
        assert 'processing_status' in summary, "Summary missing processing status"
        assert 'start_time' in summary, "Summary missing start time"
        assert 'total_processing_time_seconds' in summary, "Summary missing processing time"
        assert 'error_count' in summary, "Summary missing error count"

    @given(st.integers(min_value=1, max_value=48))
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    @pytest.mark.asyncio
    async def test_historical_performance_metrics_provision(self, hours):
        """
        Property 14b: For any monitoring data request, real-time status and historical performance metrics should be provided.

        **Feature: agentic-disaster-response, Property 14: Status Reporting**
        **Validates: Requirements 7.5**
        """
        # Create mock agent
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_enabled_tools.return_value = []

        config = AgentConfiguration(
            max_concurrent_disasters=3,
            enable_performance_monitoring=True
        )

        mock_agent = DisasterResponseAgent(mock_registry, config)

        # Get historical performance metrics
        historical_metrics = await mock_agent.get_historical_performance_metrics(hours)

        # Verify historical metrics structure
        assert 'time_period_hours' in historical_metrics, "Historical metrics missing time period"
        assert historical_metrics['time_period_hours'] == hours, "Time period mismatch"
        assert 'cutoff_time' in historical_metrics, "Historical metrics missing cutoff time"
        assert 'total_disasters' in historical_metrics, "Historical metrics missing total disasters"
        assert 'completed_disasters' in historical_metrics, "Historical metrics missing completed disasters"
        assert 'failed_disasters' in historical_metrics, "Historical metrics missing failed disasters"
        assert 'average_processing_time' in historical_metrics, "Historical metrics missing average processing time"
        assert 'success_rate' in historical_metrics, "Historical metrics missing success rate"
        assert 'performance_trends' in historical_metrics, "Historical metrics missing performance trends"

        # Verify performance trends structure
        trends = historical_metrics['performance_trends']
        assert 'processing_times' in trends, "Performance trends missing processing times"
        assert 'success_rates' in trends, "Performance trends missing success rates"
        assert 'error_counts' in trends, "Performance trends missing error counts"

        # Verify metrics are numeric and valid
        assert isinstance(historical_metrics['average_processing_time'], (
            int, float)), "Average processing time not numeric"
        assert isinstance(
            historical_metrics['success_rate'], (int, float)), "Success rate not numeric"
        assert 0 <= historical_metrics['success_rate'] <= 1, "Success rate out of valid range"

    @given(disaster_data_strategy())
    @settings(max_examples=100, verbosity=Verbosity.verbose, deadline=timedelta(seconds=10))
    @pytest.mark.asyncio
    async def test_real_time_status_monitoring(self, disaster_data):
        """
        Property 14c: For any real-time monitoring request, current system status should be provided.

        **Feature: agentic-disaster-response, Property 14: Status Reporting**
        **Validates: Requirements 7.5**
        """
        # Create mock agent
        mock_registry = MagicMock(spec=MCPToolRegistry)
        mock_registry.get_enabled_tools.return_value = []

        config = AgentConfiguration(
            max_concurrent_disasters=3,
            enable_performance_monitoring=True
        )

        mock_agent = DisasterResponseAgent(mock_registry, config)

        disaster_id = disaster_data['disaster_id']

        # Add some active disasters for testing
        from agentic_disaster_response.models.response import DisasterResponse
        from agentic_disaster_response.models.disaster_data import ProcessingStatus
        mock_response = DisasterResponse(
            disaster_id=disaster_id, processing_status=ProcessingStatus.PENDING.value)
        mock_agent.active_disasters[disaster_id] = mock_response

        # Get real-time status
        real_time_status = await mock_agent.get_real_time_status()

        # Verify real-time status structure
        assert 'timestamp' in real_time_status, "Real-time status missing timestamp"
        assert 'system_health' in real_time_status, "Real-time status missing system health"
        assert 'active_processing' in real_time_status, "Real-time status missing active processing"
        assert 'resource_utilization' in real_time_status, "Real-time status missing resource utilization"
        assert 'recent_activity' in real_time_status, "Real-time status missing recent activity"

        # Verify active processing information
        active_processing = real_time_status['active_processing']
        assert 'disaster_count' in active_processing, "Active processing missing disaster count"
        assert 'disasters' in active_processing, "Active processing missing disasters list"
        assert active_processing['disaster_count'] >= 1, "Active disaster count should be at least 1"
        assert disaster_id in active_processing['disasters'], "Test disaster not in active disasters"

        # Verify resource utilization information
        resource_util = real_time_status['resource_utilization']
        assert 'concurrent_slots_used' in resource_util, "Resource utilization missing concurrent slots used"
        assert 'concurrent_slots_available' in resource_util, "Resource utilization missing concurrent slots available"
        assert 'max_concurrent_disasters' in resource_util, "Resource utilization missing max concurrent disasters"

        # Verify resource utilization consistency
        slots_used = resource_util['concurrent_slots_used']
        slots_available = resource_util['concurrent_slots_available']
        max_concurrent = resource_util['max_concurrent_disasters']
        assert slots_used + \
            slots_available == max_concurrent, "Resource utilization slots don't add up correctly"


class TestLoggingIntegration:
    """Integration tests for logging with the disaster response agent."""

    @given(disaster_data_strategy())
    @settings(max_examples=50, verbosity=Verbosity.verbose, deadline=timedelta(seconds=15))
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_logging(self, disaster_data):
        """
        Integration test: For any disaster processing workflow, all steps should be comprehensively logged.

        **Feature: agentic-disaster-response, Property 13: Comprehensive Logging**
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        # Create mock components
        with patch.object(DisasterResponseAgent, '_retrieve_disaster_data') as mock_retrieve_data, \
                patch.object(DisasterResponseAgent, '_build_disaster_context') as mock_build_context, \
                patch.object(DisasterResponseAgent, '_analyze_disaster_priority') as mock_analyze_priority, \
                patch.object(DisasterResponseAgent, '_dispatch_disaster_alerts') as mock_dispatch:

            # Configure mocks
            mock_disaster_data = MagicMock()
            mock_disaster_data.disaster_id = disaster_data['disaster_id']
            mock_disaster_data.disaster_type = disaster_data['disaster_type']
            mock_disaster_data.severity = disaster_data['severity']
            mock_retrieve_data.return_value = mock_disaster_data

            mock_context = MagicMock()
            mock_context.disaster_info = mock_disaster_data
            mock_context.context_completeness = 0.8
            mock_context.evacuation_routes = []
            mock_context.missing_data_indicators = []
            mock_build_context.return_value = mock_context

            mock_priority = MagicMock()
            mock_priority.level = PriorityLevel.HIGH
            mock_priority.score = 0.8
            mock_priority.confidence = 0.9
            mock_analyze_priority.return_value = mock_priority

            # Mock dispatch doesn't return anything, just modifies response
            mock_dispatch.return_value = None

            disaster_id = disaster_data['disaster_id']

            # Create agent with mock registry
            mock_registry = MagicMock(spec=MCPToolRegistry)
            mock_registry.get_enabled_tools.return_value = []

            agent = DisasterResponseAgent(mock_registry)

            with LogCapture() as log_capture:
                # Process disaster event
                response = await agent.process_disaster_event(disaster_id)

                # Verify comprehensive logging occurred
                all_messages = log_capture.get_messages()
                workflow_entries = log_capture.get_workflow_entries()

                # Should have logged multiple workflow steps
                assert len(
                    workflow_entries) >= 4, f"Expected at least 4 workflow entries, got {len(workflow_entries)}"

                # Verify key workflow steps are logged
                step_types = [entry['workflow_step']
                              for entry in workflow_entries]
                step_values = [step.value if hasattr(
                    step, 'value') else step for step in step_types]
                assert 'initialization' in step_values, "Initialization step not logged"
                assert 'data_retrieval' in step_values, "Data retrieval step not logged"
                assert 'context_building' in step_values, "Context building step not logged"
                assert 'priority_analysis' in step_values, "Priority analysis step not logged"
                assert 'alert_dispatch' in step_values, "Alert dispatch step not logged"
                assert 'completion' in step_values, "Completion step not logged"

                # Verify all entries have required fields
                for entry in workflow_entries:
                    assert entry['disaster_id'] == disaster_id, "Disaster ID mismatch in workflow entry"
                    assert 'timestamp' in entry, "Workflow entry missing timestamp"
                    assert 'component' in entry, "Workflow entry missing component"
                    assert 'message' in entry, "Workflow entry missing message"
                    assert 'action_type' in entry, "Workflow entry missing action type"

                # Verify logging messages contain disaster ID
                disaster_messages = [
                    msg for msg in all_messages if disaster_id in msg]
                assert len(
                    disaster_messages) >= 3, f"Expected at least 3 messages with disaster ID, got {len(disaster_messages)}"
