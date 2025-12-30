"""
Main Disaster Response Agent orchestrator for autonomous disaster response workflow.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .context_builder import ContextBuilder
from .alert_prioritizer import AlertPrioritizer
from .alert_dispatcher import AlertDispatcher
from .models.disaster_data import DisasterData, ProcessingStatus
from .models.response import DisasterResponse, ErrorSeverity
from .models.alert_priority import AlertPriority
from .models.context import StructuredContext
from .models.mcp_tools import MCPToolRegistry
from .core.error_handler import ErrorHandler
from .core.exceptions import (
    DisasterResponseError, ContextBuildingError, PriorityAnalysisError,
    AlertDispatchError, FastAPIIntegrationError
)
from Backend.evacuation_system.main import find_evacuation_routes, get_safe_locations


async def get_disaster_data(disaster_id: str) -> DisasterData:
    """
    Mock function to retrieve disaster data from FastAPI backend.
    In a real implementation, this would query the actual backend API.
    """
    # This is a placeholder implementation for testing
    # In production, this would make an HTTP request to the FastAPI backend
    from .models.location import Location
    from .models.disaster_data import GeographicalArea, ImpactAssessment

    # Create mock disaster data for testing
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
        estimated_affected_population=1000,
        estimated_casualties=10,
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
        description=f"Mock disaster data for {disaster_id}",
        source="mock_backend"
    )


@dataclass
class AgentConfiguration:
    """Configuration for the Disaster Response Agent."""
    context_search_radius_km: float = 10.0
    max_routes_per_category: int = 3
    enable_concurrent_processing: bool = True
    max_concurrent_disasters: int = 5
    enable_performance_monitoring: bool = True
    default_alert_message_template: str = "Emergency Alert: {disaster_type} detected at {location}. Please follow evacuation instructions."


class DisasterResponseAgent:
    """
    Main orchestrator for the autonomous disaster response workflow.

    Coordinates the complete workflow from disaster data retrieval through
    alert dispatch, with comprehensive error handling and recovery mechanisms.
    """

    def __init__(
        self,
        mcp_registry: MCPToolRegistry,
        config: Optional[AgentConfiguration] = None
    ):
        """
        Initialize the Disaster Response Agent.

        Args:
            mcp_registry: Registry of available MCP tools
            config: Agent configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfiguration()
        self.logger = logging.getLogger(f"{__name__}.DisasterResponseAgent")

        # Initialize core components
        self.context_builder = ContextBuilder(
            search_radius_km=self.config.context_search_radius_km,
            max_routes_per_category=self.config.max_routes_per_category
        )
        self.alert_prioritizer = AlertPrioritizer()
        self.alert_dispatcher = AlertDispatcher(mcp_registry)
        self.error_handler = ErrorHandler()

        # Track active disasters and processing state
        self.active_disasters: Dict[str, DisasterResponse] = {}
        self.processing_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_disasters)

        # Service connection status
        self.service_connections = {
            "fastapi_backend": False,
            "mcp_tools": False,
            "context_builder": False,
            "alert_prioritizer": False,
            "alert_dispatcher": False
        }

        self.logger.info("DisasterResponseAgent initialized")

    async def initialize_connections(self) -> Dict[str, bool]:
        """
        Initialize connections to all required services and MCP tools.

        Returns:
            Dictionary indicating connection status for each service

        Raises:
            DisasterResponseError: If critical connections fail
        """
        self.logger.info("Initializing service connections...")

        connection_results = {}

        # Test FastAPI backend connection
        try:
            # Test connection by attempting to retrieve a test disaster
            test_result = await self._test_fastapi_connection()
            self.service_connections["fastapi_backend"] = test_result
            connection_results["fastapi_backend"] = test_result
            self.logger.info(
                f"FastAPI backend connection: {'OK' if test_result else 'FAILED'}")
        except Exception as e:
            self.logger.error(f"FastAPI backend connection failed: {e}")
            self.service_connections["fastapi_backend"] = False
            connection_results["fastapi_backend"] = False

        # Test MCP tools connection
        try:
            mcp_status = await self._test_mcp_tools_connection()
            self.service_connections["mcp_tools"] = mcp_status
            connection_results["mcp_tools"] = mcp_status
            self.logger.info(
                f"MCP tools connection: {'OK' if mcp_status else 'FAILED'}")
        except Exception as e:
            self.logger.error(f"MCP tools connection failed: {e}")
            self.service_connections["mcp_tools"] = False
            connection_results["mcp_tools"] = False

        # Test component initialization
        try:
            self.service_connections["context_builder"] = True
            self.service_connections["alert_prioritizer"] = True
            self.service_connections["alert_dispatcher"] = True
            connection_results.update({
                "context_builder": True,
                "alert_prioritizer": True,
                "alert_dispatcher": True
            })
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise DisasterResponseError(
                f"Failed to initialize components: {e}",
                component="DisasterResponseAgent"
            )

        # Check if critical connections are available
        critical_services = ["fastapi_backend",
                             "context_builder", "alert_prioritizer"]
        failed_critical = [
            service for service in critical_services
            if not self.service_connections[service]
        ]

        if failed_critical:
            error_msg = f"Critical service connections failed: {failed_critical}"
            self.logger.error(error_msg)
            raise DisasterResponseError(
                error_msg, component="DisasterResponseAgent")

        self.logger.info("Service connections initialized successfully")
        return connection_results

    async def process_disaster_event(self, disaster_id: str) -> DisasterResponse:
        """
        Process a single disaster event through the complete workflow.

        Args:
            disaster_id: Unique identifier for the disaster event

        Returns:
            DisasterResponse with complete processing results

        Raises:
            DisasterResponseError: If processing fails critically
        """
        async with self.processing_semaphore:
            return await self._process_disaster_internal(disaster_id)

    async def _process_disaster_internal(self, disaster_id: str) -> DisasterResponse:
        """Internal disaster processing with comprehensive error handling."""
        # Initialize response tracking
        response = DisasterResponse(
            disaster_id=disaster_id,
            processing_status=ProcessingStatus.PENDING.value
        )
        self.active_disasters[disaster_id] = response

        self.logger.info(f"Starting disaster processing for {disaster_id}")

        try:
            # Step 1: Retrieve disaster data from FastAPI backend
            response.processing_status = ProcessingStatus.CONTEXT_BUILDING.value
            disaster_data = await self._retrieve_disaster_data(disaster_id)

            # Step 2: Build comprehensive context
            context = await self._build_disaster_context(disaster_data, response)
            response.context = context

            # Step 3: Analyze priority
            response.processing_status = ProcessingStatus.PRIORITY_ANALYSIS.value
            priority = await self._analyze_disaster_priority(context, response)
            response.priority = priority

            # Step 4: Dispatch alerts
            response.processing_status = ProcessingStatus.ALERT_DISPATCH.value
            await self._dispatch_disaster_alerts(priority, context, response)

            # Mark as completed
            response.processing_status = ProcessingStatus.COMPLETED.value
            response.mark_completed()

            self.logger.info(
                f"Disaster processing completed for {disaster_id} in "
                f"{response.total_processing_time_seconds:.2f}s"
            )

            return response

        except Exception as e:
            # Handle processing failure
            response.processing_status = ProcessingStatus.FAILED.value
            error_record = response.add_error(
                component="DisasterResponseAgent",
                severity=ErrorSeverity.CRITICAL,
                error_type=type(e).__name__,
                error_message=str(e),
                context={"disaster_id": disaster_id}
            )

            self.logger.error(
                f"Disaster processing failed for {disaster_id}: {e}")

            # Attempt error recovery
            recovery_result = await self.error_handler.handle_error(
                e, {"disaster_id": disaster_id,
                    "component": "DisasterResponseAgent"}
            )

            if recovery_result.get("status") == "recovered":
                self.logger.info(
                    f"Recovery successful for disaster {disaster_id}")
                error_record.recovery_action_taken = "Automatic recovery successful"
                error_record.resolved = True
            else:
                error_record.recovery_action_taken = f"Recovery failed: {recovery_result.get('reason', 'Unknown')}"

            response.mark_completed()
            return response

        finally:
            # Clean up active disaster tracking
            if disaster_id in self.active_disasters:
                del self.active_disasters[disaster_id]

    async def _retrieve_disaster_data(self, disaster_id: str) -> DisasterData:
        """Retrieve disaster data from FastAPI backend with error handling."""
        try:
            self.logger.info(f"Retrieving disaster data for {disaster_id}")

            # Use existing FastAPI backend function
            disaster_data = await get_disaster_data(disaster_id)

            if not disaster_data:
                raise FastAPIIntegrationError(
                    f"No disaster data found for ID: {disaster_id}",
                    disaster_id=disaster_id,
                    component="FastAPIBackend"
                )

            # Validate disaster data completeness
            self._validate_disaster_data(disaster_data)

            self.logger.info(
                f"Successfully retrieved disaster data for {disaster_id}")
            return disaster_data

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve disaster data for {disaster_id}: {e}")
            raise FastAPIIntegrationError(
                f"Failed to retrieve disaster data: {e}",
                disaster_id=disaster_id,
                component="FastAPIBackend"
            ) from e

    async def _build_disaster_context(
        self, disaster_data: DisasterData, response: DisasterResponse
    ) -> StructuredContext:
        """Build disaster context with error handling and fallback."""
        try:
            self.logger.info(
                f"Building context for disaster {disaster_data.disaster_id}")

            context = await self.context_builder.build_context(disaster_data)

            self.logger.info(
                f"Context built successfully for {disaster_data.disaster_id} "
                f"with {context.context_completeness:.2f} completeness"
            )

            return context

        except Exception as e:
            self.logger.error(
                f"Context building failed for {disaster_data.disaster_id}: {e}")

            # Add error record
            response.add_error(
                component="ContextBuilder",
                severity=ErrorSeverity.HIGH,
                error_type=type(e).__name__,
                error_message=str(e),
                recovery_action="Attempting fallback context"
            )

            # Attempt to create minimal fallback context
            try:
                fallback_context = await self._create_fallback_context(disaster_data)
                self.logger.warning(
                    f"Using fallback context for disaster {disaster_data.disaster_id}"
                )
                return fallback_context
            except Exception as fallback_error:
                raise ContextBuildingError(
                    f"Context building and fallback both failed: {e}",
                    disaster_id=disaster_data.disaster_id,
                    component="ContextBuilder"
                ) from fallback_error

    async def _analyze_disaster_priority(
        self, context: StructuredContext, response: DisasterResponse
    ) -> AlertPriority:
        """Analyze disaster priority with fallback handling."""
        try:
            self.logger.info(
                f"Analyzing priority for disaster {context.disaster_info.disaster_id}")

            priority = self.alert_prioritizer.analyze_priority_with_fallback(
                context)

            self.logger.info(
                f"Priority analysis completed for {context.disaster_info.disaster_id}: "
                f"{priority.level.value} (score: {priority.score:.3f})"
            )

            return priority

        except Exception as e:
            self.logger.error(
                f"Priority analysis failed for {context.disaster_info.disaster_id}: {e}")

            # Add error record
            response.add_error(
                component="AlertPrioritizer",
                severity=ErrorSeverity.HIGH,
                error_type=type(e).__name__,
                error_message=str(e),
                recovery_action="Using fallback HIGH priority"
            )

            # Use fallback priority (AlertPrioritizer handles this internally)
            fallback_priority = self.alert_prioritizer._create_fallback_priority(
                f"Priority analysis failed: {e}"
            )

            return fallback_priority

    async def _dispatch_disaster_alerts(
        self, priority: AlertPriority, context: StructuredContext, response: DisasterResponse
    ) -> None:
        """Dispatch disaster alerts with comprehensive error handling."""
        try:
            disaster_id = context.disaster_info.disaster_id
            self.logger.info(f"Dispatching alerts for disaster {disaster_id}")

            # Generate alert message
            alert_message = self._generate_alert_message(context, priority)

            # Dispatch alerts through MCP tools
            dispatch_result = await self.alert_dispatcher.dispatch_alerts(
                priority=priority,
                context=context,
                message=alert_message
            )

            # Convert dispatch result to response format
            from .models.response import DispatchResult as ResponseDispatchResult, DispatchStatus

            for execution_result in dispatch_result.execution_results:
                status = DispatchStatus.SUCCESS if execution_result.status.value == "success" else DispatchStatus.FAILED

                response_dispatch = ResponseDispatchResult(
                    dispatch_id=f"{disaster_id}_{execution_result.tool_name}_{int(datetime.now().timestamp())}",
                    mcp_tool_name=execution_result.tool_name,
                    status=status,
                    timestamp=datetime.now(),
                    recipients_count=len(context.affected_population.total_population if hasattr(
                        context.affected_population, 'total_population') else []),
                    successful_deliveries=1 if status == DispatchStatus.SUCCESS else 0,
                    failed_deliveries=1 if status == DispatchStatus.FAILED else 0,
                    error_message=execution_result.error_message,
                    retry_count=getattr(execution_result, 'retry_count', 0),
                    execution_time_seconds=execution_result.execution_time_ms /
                    1000.0 if execution_result.execution_time_ms else None
                )
                response.dispatch_results.append(response_dispatch)

            if dispatch_result.success:
                self.logger.info(
                    f"Alert dispatch completed successfully for {disaster_id}: "
                    f"{dispatch_result.successful_dispatches}/{dispatch_result.total_tools_attempted} tools succeeded"
                )
            else:
                self.logger.error(
                    f"Alert dispatch failed for {disaster_id}: {dispatch_result.error_summary}"
                )
                response.add_error(
                    component="AlertDispatcher",
                    severity=ErrorSeverity.HIGH,
                    error_type="AlertDispatchError",
                    error_message=dispatch_result.error_summary or "Alert dispatch failed",
                    context={
                        "successful_dispatches": dispatch_result.successful_dispatches}
                )

        except Exception as e:
            self.logger.error(
                f"Alert dispatch failed for {context.disaster_info.disaster_id}: {e}")

            response.add_error(
                component="AlertDispatcher",
                severity=ErrorSeverity.CRITICAL,
                error_type=type(e).__name__,
                error_message=str(e)
            )

            raise AlertDispatchError(
                f"Alert dispatch failed: {e}",
                disaster_id=context.disaster_info.disaster_id,
                component="AlertDispatcher"
            ) from e

    def _generate_alert_message(self, context: StructuredContext, priority: AlertPriority) -> str:
        """Generate alert message based on context and priority."""
        disaster_info = context.disaster_info

        # Use template to generate message
        message = self.config.default_alert_message_template.format(
            disaster_type=disaster_info.disaster_type.value.replace(
                '_', ' ').title(),
            location=disaster_info.location.address or f"coordinates {disaster_info.location.latitude:.4f}, {disaster_info.location.longitude:.4f}",
            severity=disaster_info.severity.value.upper(),
            priority=priority.level.value.upper()
        )

        # Add evacuation information if available
        if context.evacuation_routes:
            route_count = len(context.evacuation_routes)
            message += f" {route_count} evacuation route{'s' if route_count != 1 else ''} available."

        # Add urgency information based on priority
        if priority.level.value in ['critical', 'high']:
            message += " IMMEDIATE ACTION REQUIRED."

        return message

    async def _create_fallback_context(self, disaster_data: DisasterData) -> StructuredContext:
        """Create minimal fallback context when context building fails."""
        from .models.context import (
            GeographicalContext, PopulationData, ResourceInventory, RiskMetrics
        )

        # Create minimal context with available data
        geographical_context = GeographicalContext(
            affected_areas=[
                area.center for area in disaster_data.affected_areas],
            safe_locations=[],
            blocked_routes=[],
            accessible_routes=[]
        )

        population_data = PopulationData(
            total_population=disaster_data.estimated_impact.estimated_affected_population,
            vulnerable_population=int(
                disaster_data.estimated_impact.estimated_affected_population * 0.2),
            current_occupancy=disaster_data.estimated_impact.estimated_affected_population,
            population_density_per_km2=100.0  # Default estimate
        )

        resource_inventory = ResourceInventory(
            available_shelters=1,
            shelter_capacity=100,
            medical_facilities=1,
            emergency_vehicles=1,
            communication_systems=1,
            backup_power_systems=1
        )

        risk_metrics = RiskMetrics(
            overall_risk_score=0.7,  # Default high risk for fallback
            evacuation_difficulty=0.8,  # Assume difficult evacuation
            time_criticality=0.8,  # Assume time critical
            resource_availability=0.3,  # Assume limited resources
            weather_impact=0.5,
            traffic_congestion=0.5
        )

        return StructuredContext(
            disaster_info=disaster_data,
            geographical_context=geographical_context,
            evacuation_routes=[],
            affected_population=population_data,
            available_resources=resource_inventory,
            risk_assessment=risk_metrics,
            context_completeness=0.3,  # Low completeness for fallback
            missing_data_indicators=["safe_locations",
                                     "evacuation_routes", "weather_conditions"]
        )

    def _validate_disaster_data(self, disaster_data: DisasterData) -> None:
        """Validate disaster data completeness and format."""
        errors = []

        if not disaster_data.disaster_id:
            errors.append("Missing disaster ID")

        if not disaster_data.disaster_type:
            errors.append("Missing disaster type")

        if not disaster_data.location:
            errors.append("Missing disaster location")

        if not disaster_data.affected_areas:
            errors.append("Missing affected areas")

        if not disaster_data.estimated_impact:
            errors.append("Missing impact assessment")
        elif disaster_data.estimated_impact.estimated_affected_population <= 0:
            errors.append("Invalid affected population count")

        if errors:
            raise FastAPIIntegrationError(
                f"Invalid disaster data: {'; '.join(errors)}",
                disaster_id=disaster_data.disaster_id,
                component="DataValidation"
            )

    async def _test_fastapi_connection(self) -> bool:
        """Test connection to FastAPI backend."""
        try:
            # This would test the actual connection in a real implementation
            # For now, we'll assume it's available if the import worked
            return True
        except Exception:
            return False

    async def _test_mcp_tools_connection(self) -> bool:
        """Test connection to MCP tools."""
        try:
            # Test if MCP tools are available and responsive
            # This would ping actual MCP tools in a real implementation
            return len(self.alert_dispatcher.registry.get_enabled_tools()) > 0
        except Exception:
            return False

    def get_active_disasters(self) -> Dict[str, DisasterResponse]:
        """Get currently active disaster processing operations."""
        return self.active_disasters.copy()

    def get_service_status(self) -> Dict[str, bool]:
        """Get current status of all service connections."""
        return self.service_connections.copy()

    async def handle_concurrent_disasters(self, disaster_ids: List[str]) -> List[DisasterResponse]:
        """
        Handle multiple concurrent disasters efficiently with resource management.

        Args:
            disaster_ids: List of disaster IDs to process concurrently

        Returns:
            List of DisasterResponse objects for all processed disasters

        Raises:
            DisasterResponseError: If concurrent processing fails critically
        """
        if not disaster_ids:
            return []

        self.logger.info(
            f"Starting concurrent processing of {len(disaster_ids)} disasters")

        # Limit concurrent processing based on configuration
        if len(disaster_ids) > self.config.max_concurrent_disasters:
            self.logger.warning(
                f"Requested {len(disaster_ids)} concurrent disasters exceeds limit of "
                f"{self.config.max_concurrent_disasters}. Processing in batches."
            )

        # Process disasters in batches if needed
        all_responses = []
        batch_size = self.config.max_concurrent_disasters

        for i in range(0, len(disaster_ids), batch_size):
            batch = disaster_ids[i:i + batch_size]
            self.logger.info(
                f"Processing batch {i//batch_size + 1}: {len(batch)} disasters")

            batch_responses = await self._process_disaster_batch(batch)
            all_responses.extend(batch_responses)

        self.logger.info(
            f"Concurrent processing completed: {len(all_responses)} disasters processed")
        return all_responses

    async def _process_disaster_batch(self, disaster_ids: List[str]) -> List[DisasterResponse]:
        """Process a batch of disasters concurrently."""
        # Create tasks for concurrent processing
        tasks = []
        for disaster_id in disaster_ids:
            task = asyncio.create_task(
                self.process_disaster_event(disaster_id),
                name=f"disaster_{disaster_id}"
            )
            tasks.append(task)

        # Wait for all tasks to complete, handling exceptions
        responses = []
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(completed_tasks):
            disaster_id = disaster_ids[i]

            if isinstance(result, Exception):
                # Create error response for failed disaster
                error_response = DisasterResponse(
                    disaster_id=disaster_id,
                    processing_status=ProcessingStatus.FAILED.value
                )
                error_response.add_error(
                    component="DisasterResponseAgent",
                    severity=ErrorSeverity.CRITICAL,
                    error_type=type(result).__name__,
                    error_message=str(result),
                    context={"disaster_id": disaster_id,
                             "concurrent_processing": True}
                )
                error_response.mark_completed()
                responses.append(error_response)

                self.logger.error(
                    f"Concurrent processing failed for disaster {disaster_id}: {result}")
            else:
                responses.append(result)

        return responses

    async def recover_from_failure(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement comprehensive error recovery and fallback procedures.

        Args:
            disaster_id: ID of the disaster that failed processing
            failure_context: Context information about the failure

        Returns:
            Dictionary with recovery results and actions taken
        """
        self.logger.info(f"Attempting recovery for disaster {disaster_id}")

        recovery_actions = []
        recovery_success = False

        try:
            # Step 1: Assess failure type and determine recovery strategy
            failure_type = failure_context.get("error_type", "unknown")
            failed_component = failure_context.get("component", "unknown")

            # Step 2: Attempt component-specific recovery
            if failed_component == "FastAPIBackend":
                recovery_result = await self._recover_fastapi_failure(disaster_id, failure_context)
                recovery_actions.append(
                    f"FastAPI recovery: {recovery_result['status']}")
                recovery_success = recovery_result.get("success", False)

            elif failed_component == "ContextBuilder":
                recovery_result = await self._recover_context_failure(disaster_id, failure_context)
                recovery_actions.append(
                    f"Context recovery: {recovery_result['status']}")
                recovery_success = recovery_result.get("success", False)

            elif failed_component == "AlertPrioritizer":
                recovery_result = await self._recover_priority_failure(disaster_id, failure_context)
                recovery_actions.append(
                    f"Priority recovery: {recovery_result['status']}")
                recovery_success = recovery_result.get("success", False)

            elif failed_component == "AlertDispatcher":
                recovery_result = await self._recover_dispatch_failure(disaster_id, failure_context)
                recovery_actions.append(
                    f"Dispatch recovery: {recovery_result['status']}")
                recovery_success = recovery_result.get("success", False)

            # Step 3: If component-specific recovery fails, try graceful degradation
            if not recovery_success:
                degradation_result = await self._implement_graceful_degradation(disaster_id, failure_context)
                recovery_actions.append(
                    f"Graceful degradation: {degradation_result['status']}")
                recovery_success = degradation_result.get("success", False)

            # Step 4: Log recovery results
            if recovery_success:
                self.logger.info(
                    f"Recovery successful for disaster {disaster_id}: {recovery_actions}")
            else:
                self.logger.error(
                    f"Recovery failed for disaster {disaster_id}: {recovery_actions}")

            return {
                "disaster_id": disaster_id,
                "recovery_success": recovery_success,
                "recovery_actions": recovery_actions,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(
                f"Recovery process failed for disaster {disaster_id}: {e}")
            return {
                "disaster_id": disaster_id,
                "recovery_success": False,
                "recovery_actions": recovery_actions + [f"Recovery process error: {str(e)}"],
                "timestamp": datetime.now().isoformat()
            }

    async def _recover_fastapi_failure(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from FastAPI backend failures."""
        # Try to use cached data if available
        cached_data = failure_context.get("cached_data")
        if cached_data:
            self.logger.info(f"Using cached data for disaster {disaster_id}")
            return {"success": True, "status": "used_cached_data"}

        # Try alternative data sources (placeholder for real implementation)
        try:
            # In a real implementation, this would try alternative APIs or data sources
            self.logger.info(
                f"Attempting alternative data source for disaster {disaster_id}")
            await asyncio.sleep(0.1)  # Simulate alternative data retrieval
            return {"success": True, "status": "alternative_data_source"}
        except Exception:
            return {"success": False, "status": "all_data_sources_failed"}

    async def _recover_context_failure(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from context building failures."""
        try:
            # Attempt to create minimal context with available data
            disaster_data = failure_context.get("disaster_data")
            if disaster_data:
                minimal_context = await self._create_fallback_context(disaster_data)
                self.logger.info(
                    f"Created fallback context for disaster {disaster_id}")
                return {"success": True, "status": "fallback_context_created", "context": minimal_context}
        except Exception as e:
            self.logger.error(
                f"Fallback context creation failed for disaster {disaster_id}: {e}")

        return {"success": False, "status": "context_recovery_failed"}

    async def _recover_priority_failure(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from priority analysis failures."""
        try:
            # Use fallback HIGH priority as specified in requirements
            fallback_priority = self.alert_prioritizer._create_fallback_priority(
                f"Recovery fallback for disaster {disaster_id}"
            )
            self.logger.info(
                f"Using fallback HIGH priority for disaster {disaster_id}")
            return {"success": True, "status": "fallback_priority_assigned", "priority": fallback_priority}
        except Exception as e:
            self.logger.error(
                f"Priority recovery failed for disaster {disaster_id}: {e}")
            return {"success": False, "status": "priority_recovery_failed"}

    async def _recover_dispatch_failure(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from alert dispatch failures."""
        try:
            # Try alternative alert mechanisms
            alternative_methods = ["email_backup",
                                   "sms_backup", "local_broadcast"]

            for method in alternative_methods:
                try:
                    # Simulate alternative alert method
                    self.logger.info(
                        f"Attempting alternative alert method {method} for disaster {disaster_id}")
                    await asyncio.sleep(0.1)  # Simulate alternative dispatch
                    return {"success": True, "status": f"alternative_dispatch_{method}"}
                except Exception:
                    continue

            return {"success": False, "status": "all_dispatch_methods_failed"}
        except Exception as e:
            self.logger.error(
                f"Dispatch recovery failed for disaster {disaster_id}: {e}")
            return {"success": False, "status": "dispatch_recovery_error"}

    async def _implement_graceful_degradation(self, disaster_id: str, failure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Implement graceful degradation for partial system failures."""
        try:
            degraded_capabilities = []

            # Identify what functionality is still available
            if self.service_connections.get("fastapi_backend", False):
                degraded_capabilities.append("data_retrieval")

            if self.service_connections.get("context_builder", False):
                degraded_capabilities.append("basic_context")

            if self.service_connections.get("alert_prioritizer", False):
                degraded_capabilities.append("priority_analysis")

            # If we have minimal capabilities, continue with reduced functionality
            if len(degraded_capabilities) >= 2:
                self.logger.info(
                    f"Continuing with degraded capabilities for disaster {disaster_id}: {degraded_capabilities}"
                )
                return {
                    "success": True,
                    "status": "graceful_degradation_active",
                    "available_capabilities": degraded_capabilities
                }
            else:
                return {
                    "success": False,
                    "status": "insufficient_capabilities_for_degradation",
                    "available_capabilities": degraded_capabilities
                }

        except Exception as e:
            self.logger.error(
                f"Graceful degradation failed for disaster {disaster_id}: {e}")
            return {"success": False, "status": "degradation_implementation_failed"}

    async def handle_partial_system_failure(self, failed_components: List[str]) -> Dict[str, Any]:
        """
        Handle partial system failures by continuing with available functionality.

        Args:
            failed_components: List of component names that have failed

        Returns:
            Dictionary with system status and available functionality
        """
        self.logger.warning(
            f"Handling partial system failure: {failed_components}")

        # Update service connection status
        for component in failed_components:
            if component in self.service_connections:
                self.service_connections[component] = False

        # Determine available functionality
        available_functionality = []
        degraded_functionality = []

        # Check what's still working
        if self.service_connections.get("fastapi_backend", False):
            available_functionality.append("disaster_data_retrieval")
        else:
            degraded_functionality.append("using_cached_or_manual_data")

        if self.service_connections.get("context_builder", False):
            available_functionality.append("context_building")
        else:
            degraded_functionality.append("minimal_context_only")

        if self.service_connections.get("alert_prioritizer", False):
            available_functionality.append("priority_analysis")
        else:
            degraded_functionality.append("fallback_high_priority")

        if self.service_connections.get("mcp_tools", False):
            available_functionality.append("alert_dispatch")
        else:
            degraded_functionality.append("alternative_alert_methods")

        # Determine if system can continue operating
        critical_components = ["context_builder", "alert_prioritizer"]
        critical_failures = [
            comp for comp in failed_components if comp in critical_components]

        can_continue = len(critical_failures) == 0 or len(
            available_functionality) >= 2

        result = {
            "can_continue_operation": can_continue,
            "available_functionality": available_functionality,
            "degraded_functionality": degraded_functionality,
            "failed_components": failed_components,
            "recovery_recommendations": self._generate_recovery_recommendations(failed_components)
        }

        if can_continue:
            self.logger.info(
                f"System can continue with degraded functionality: {available_functionality}")
        else:
            self.logger.error(
                f"System cannot continue operation due to critical failures: {critical_failures}")

        return result

    def _generate_recovery_recommendations(self, failed_components: List[str]) -> List[str]:
        """Generate recommendations for recovering from component failures."""
        recommendations = []

        for component in failed_components:
            if component == "fastapi_backend":
                recommendations.append(
                    "Check FastAPI backend service status and network connectivity")
            elif component == "mcp_tools":
                recommendations.append(
                    "Verify MCP tool configurations and endpoints")
            elif component == "context_builder":
                recommendations.append(
                    "Check external data sources and API connections")
            elif component == "alert_prioritizer":
                recommendations.append(
                    "Verify priority analysis algorithms and data dependencies")
            elif component == "alert_dispatcher":
                recommendations.append(
                    "Check alert delivery channels and MCP tool availability")

        recommendations.append("Consider restarting failed services")
        recommendations.append(
            "Check system logs for detailed error information")

        return recommendations

    async def monitor_system_health(self) -> Dict[str, Any]:
        """
        Monitor system health and automatically recover when components are restored.

        Returns:
            Dictionary with current system health status
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "component_status": {},
            "active_disasters": len(self.active_disasters),
            "recovery_actions": []
        }

        try:
            # Test each component
            component_tests = {
                "fastapi_backend": self._test_fastapi_connection,
                "mcp_tools": self._test_mcp_tools_connection,
                "context_builder": lambda: asyncio.create_task(asyncio.sleep(0.01)) or True,
                "alert_prioritizer": lambda: asyncio.create_task(asyncio.sleep(0.01)) or True,
                "alert_dispatcher": lambda: asyncio.create_task(asyncio.sleep(0.01)) or True
            }

            for component, test_func in component_tests.items():
                try:
                    previous_status = self.service_connections.get(
                        component, False)
                    current_status = await test_func()

                    health_status["component_status"][component] = current_status
                    self.service_connections[component] = current_status

                    # Check for recovery
                    if not previous_status and current_status:
                        recovery_msg = f"Component {component} has been restored"
                        health_status["recovery_actions"].append(recovery_msg)
                        self.logger.info(recovery_msg)

                except Exception as e:
                    health_status["component_status"][component] = False
                    self.service_connections[component] = False
                    self.logger.error(
                        f"Health check failed for {component}: {e}")

            # Determine overall health
            healthy_components = sum(
                1 for status in health_status["component_status"].values() if status)
            total_components = len(health_status["component_status"])

            if healthy_components == total_components:
                health_status["overall_health"] = "healthy"
            elif healthy_components >= total_components * 0.7:
                health_status["overall_health"] = "degraded"
            else:
                health_status["overall_health"] = "critical"

            return health_status

        except Exception as e:
            self.logger.error(f"System health monitoring failed: {e}")
            health_status["overall_health"] = "monitoring_failed"
            health_status["error"] = str(e)
            return health_status

    async def generate_status_report(self, disaster_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive status report for completed workflows.

        Args:
            disaster_id: Optional specific disaster ID to report on

        Returns:
            Dictionary with comprehensive status information
        """
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "system_status": await self.monitor_system_health(),
            "active_disasters": len(self.active_disasters),
            "disaster_summaries": []
        }

        try:
            # If specific disaster requested, report on it
            if disaster_id:
                if disaster_id in self.active_disasters:
                    disaster_response = self.active_disasters[disaster_id]
                    report["disaster_summaries"].append(
                        self._create_disaster_summary(disaster_response)
                    )
                else:
                    report["error"] = f"Disaster {disaster_id} not found in active disasters"

            # Otherwise, report on all active disasters
            else:
                for disaster_response in self.active_disasters.values():
                    report["disaster_summaries"].append(
                        self._create_disaster_summary(disaster_response)
                    )

            # Add performance metrics
            report["performance_metrics"] = await self._calculate_performance_metrics()

            # Add error summary
            report["error_summary"] = self._generate_error_summary()

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate status report: {e}")
            report["report_error"] = str(e)
            return report

    def _create_disaster_summary(self, disaster_response: DisasterResponse) -> Dict[str, Any]:
        """Create summary information for a disaster response."""
        summary = {
            "disaster_id": disaster_response.disaster_id,
            "processing_status": disaster_response.processing_status,
            "start_time": disaster_response.start_time.isoformat(),
            "completion_time": disaster_response.completion_time.isoformat() if disaster_response.completion_time else None,
            "total_processing_time_seconds": disaster_response.total_processing_time_seconds,
            "error_count": len(disaster_response.errors),
            "critical_errors": disaster_response.has_critical_errors,
            "dispatch_success_rate": disaster_response.success_rate
        }

        # Add context information if available
        if disaster_response.context:
            summary["context_completeness"] = disaster_response.context.context_completeness
            summary["affected_population"] = disaster_response.context.affected_population.total_population
            summary["evacuation_routes_count"] = len(
                disaster_response.context.evacuation_routes)

        # Add priority information if available
        if disaster_response.priority:
            summary["priority_level"] = disaster_response.priority.level.value
            summary["priority_score"] = disaster_response.priority.score
            summary["priority_confidence"] = disaster_response.priority.confidence

        # Add dispatch results summary
        if disaster_response.dispatch_results:
            successful_dispatches = sum(
                1 for result in disaster_response.dispatch_results
                if result.status.value == "success"
            )
            summary["successful_dispatches"] = successful_dispatches
            summary["total_dispatch_attempts"] = len(
                disaster_response.dispatch_results)

        return summary

    async def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate system performance metrics."""
        metrics = {
            "average_processing_time_seconds": 0.0,
            "total_disasters_processed": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "component_performance": {}
        }

        try:
            # Calculate metrics from active disasters
            completed_disasters = [
                response for response in self.active_disasters.values()
                if response.processing_status == ProcessingStatus.COMPLETED.value
            ]

            if completed_disasters:
                # Average processing time
                total_time = sum(
                    response.total_processing_time_seconds or 0
                    for response in completed_disasters
                )
                metrics["average_processing_time_seconds"] = total_time / \
                    len(completed_disasters)

                # Success rate
                successful_disasters = sum(
                    1 for response in completed_disasters
                    if not response.has_critical_errors
                )
                metrics["success_rate"] = successful_disasters / \
                    len(completed_disasters)
                metrics["error_rate"] = 1.0 - metrics["success_rate"]

            metrics["total_disasters_processed"] = len(completed_disasters)

            # Component performance from alert dispatcher
            if hasattr(self.alert_dispatcher, 'get_tool_performance_stats'):
                metrics["component_performance"]["alert_dispatcher"] = (
                    self.alert_dispatcher.get_tool_performance_stats()
                )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            metrics["calculation_error"] = str(e)
            return metrics

    def _generate_error_summary(self) -> Dict[str, Any]:
        """Generate summary of errors across all disasters."""
        error_summary = {
            "total_errors": 0,
            "critical_errors": 0,
            "errors_by_component": {},
            "errors_by_type": {},
            "recent_errors": []
        }

        try:
            all_errors = []
            for disaster_response in self.active_disasters.values():
                all_errors.extend(disaster_response.errors)

            error_summary["total_errors"] = len(all_errors)

            # Count by severity
            error_summary["critical_errors"] = sum(
                1 for error in all_errors
                if error.severity == ErrorSeverity.CRITICAL
            )

            # Count by component
            for error in all_errors:
                component = error.component
                if component not in error_summary["errors_by_component"]:
                    error_summary["errors_by_component"][component] = 0
                error_summary["errors_by_component"][component] += 1

            # Count by type
            for error in all_errors:
                error_type = error.error_type
                if error_type not in error_summary["errors_by_type"]:
                    error_summary["errors_by_type"][error_type] = 0
                error_summary["errors_by_type"][error_type] += 1

            # Recent errors (last 10)
            recent_errors = sorted(
                all_errors, key=lambda e: e.timestamp, reverse=True)[:10]
            error_summary["recent_errors"] = [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "component": error.component,
                    "severity": error.severity.value,
                    "error_type": error.error_type,
                    "message": error.error_message[:100] + "..." if len(error.error_message) > 100 else error.error_message
                }
                for error in recent_errors
            ]

            return error_summary

        except Exception as e:
            self.logger.error(f"Failed to generate error summary: {e}")
            error_summary["summary_error"] = str(e)
            return error_summary

    async def get_real_time_status(self) -> Dict[str, Any]:
        """
        Get real-time status and metrics for monitoring dashboards.

        Returns:
            Dictionary with real-time system status
        """
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "system_health": await self.monitor_system_health(),
                "active_processing": {
                    "disaster_count": len(self.active_disasters),
                    "disasters": list(self.active_disasters.keys())
                },
                "resource_utilization": {
                    "concurrent_slots_used": self.config.max_concurrent_disasters - self.processing_semaphore._value,
                    "concurrent_slots_available": self.processing_semaphore._value,
                    "max_concurrent_disasters": self.config.max_concurrent_disasters
                },
                "recent_activity": await self._get_recent_activity()
            }

            return status

        except Exception as e:
            self.logger.error(f"Failed to get real-time status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "system_health": {"overall_health": "unknown"}
            }

    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent activity for real-time monitoring."""
        try:
            activities = []

            # Add recent disaster processing activities
            # Last 5 disasters
            for disaster_response in list(self.active_disasters.values())[-5:]:
                activities.append({
                    "type": "disaster_processing",
                    "disaster_id": disaster_response.disaster_id,
                    "status": disaster_response.processing_status,
                    "timestamp": disaster_response.start_time.isoformat(),
                    "duration_seconds": disaster_response.total_processing_time_seconds
                })

            # Sort by timestamp (most recent first)
            activities.sort(key=lambda x: x["timestamp"], reverse=True)

            return activities[:10]  # Return last 10 activities

        except Exception as e:
            self.logger.error(f"Failed to get recent activity: {e}")
            return []

    async def get_historical_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get historical performance metrics for the specified time period.

        Args:
            hours: Number of hours to look back for metrics

        Returns:
            Dictionary with historical performance data
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # In a real implementation, this would query a database or metrics store
            # For now, we'll use the active disasters as a proxy
            relevant_disasters = [
                response for response in self.active_disasters.values()
                if response.start_time >= cutoff_time
            ]

            metrics = {
                "time_period_hours": hours,
                "cutoff_time": cutoff_time.isoformat(),
                "total_disasters": len(relevant_disasters),
                "completed_disasters": 0,
                "failed_disasters": 0,
                "average_processing_time": 0.0,
                "success_rate": 0.0,
                "performance_trends": {
                    "processing_times": [],
                    "success_rates": [],
                    "error_counts": []
                }
            }

            if relevant_disasters:
                completed = [
                    d for d in relevant_disasters
                    if d.processing_status == ProcessingStatus.COMPLETED.value
                ]
                failed = [
                    d for d in relevant_disasters
                    if d.processing_status == ProcessingStatus.FAILED.value
                ]

                metrics["completed_disasters"] = len(completed)
                metrics["failed_disasters"] = len(failed)

                if completed:
                    total_time = sum(
                        d.total_processing_time_seconds or 0 for d in completed
                    )
                    metrics["average_processing_time"] = total_time / \
                        len(completed)

                    successful = sum(
                        1 for d in completed if not d.has_critical_errors)
                    metrics["success_rate"] = successful / len(completed)

                # Generate hourly trends (simplified)
                for hour in range(hours):
                    hour_start = cutoff_time + timedelta(hours=hour)
                    hour_end = hour_start + timedelta(hours=1)

                    hour_disasters = [
                        d for d in relevant_disasters
                        if hour_start <= d.start_time < hour_end
                    ]

                    if hour_disasters:
                        hour_completed = [
                            d for d in hour_disasters
                            if d.processing_status == ProcessingStatus.COMPLETED.value
                        ]

                        avg_time = 0.0
                        if hour_completed:
                            avg_time = sum(
                                d.total_processing_time_seconds or 0 for d in hour_completed
                            ) / len(hour_completed)

                        success_rate = 0.0
                        if hour_completed:
                            successful = sum(
                                1 for d in hour_completed if not d.has_critical_errors)
                            success_rate = successful / len(hour_completed)

                        error_count = sum(len(d.errors)
                                          for d in hour_disasters)

                        metrics["performance_trends"]["processing_times"].append({
                            "hour": hour_start.isoformat(),
                            "average_time": avg_time
                        })
                        metrics["performance_trends"]["success_rates"].append({
                            "hour": hour_start.isoformat(),
                            "success_rate": success_rate
                        })
                        metrics["performance_trends"]["error_counts"].append({
                            "hour": hour_start.isoformat(),
                            "error_count": error_count
                        })

            return metrics

        except Exception as e:
            self.logger.error(
                f"Failed to get historical performance metrics: {e}")
            return {
                "time_period_hours": hours,
                "error": str(e)
            }
