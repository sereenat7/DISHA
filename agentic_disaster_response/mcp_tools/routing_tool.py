"""
Concrete implementation of MCP Routing Tool for evacuation route management.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
import httpx

from agentic_disaster_response.mcp_integration import MCPTool, AlertData, ExecutionResult, ExecutionStatus
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, ToolConfiguration
from agentic_disaster_response.models.alert_priority import PriorityLevel
from agentic_disaster_response.core.exceptions import MCPToolError


class RoutingMCPTool(MCPTool):
    """
    Concrete implementation of MCP Routing Tool for evacuation route management.

    This tool handles:
    - Real-time route optimization
    - Traffic and capacity monitoring
    - Alternative route calculation
    - Route dissemination to navigation systems
    - Dynamic route updates based on conditions
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=45.0)
        self.routing_services = {
            "primary_routing": self._calculate_primary_routes,
            "alternative_routing": self._calculate_alternative_routes,
            "real_time_updates": self._update_routes_real_time,
            "capacity_monitoring": self._monitor_route_capacity,
            "navigation_integration": self._integrate_with_navigation
        }

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute routing operations for evacuation management."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing routing tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for routing tool {self.config.tool_name}")

            # Format data for this tool
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Determine routing operations based on priority
            operations = self._select_operations_for_priority(
                alert_data.priority.level, tool_config)

            # Execute routing operations
            operation_results = []
            successful_operations = 0
            failed_operations = 0

            for operation in operations:
                try:
                    operation_result = await self._execute_routing_operation(
                        operation, formatted_data, tool_config
                    )
                    operation_results.append(operation_result)

                    if operation_result.get("success", False):
                        successful_operations += 1
                    else:
                        failed_operations += 1

                except Exception as e:
                    self.logger.error(
                        f"Routing operation {operation} failed: {e}")
                    operation_results.append({
                        "operation": operation,
                        "success": False,
                        "error": str(e)
                    })
                    failed_operations += 1

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Determine overall success
            overall_success = successful_operations > 0
            status = ExecutionStatus.SUCCESS if overall_success else ExecutionStatus.FAILURE

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "operations_attempted": len(operations),
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "operation_results": operation_results,
                "routes_processed": len(alert_data.context.evacuation_routes),
                "alternative_routes_generated": self._count_alternative_routes(operation_results),
                "navigation_systems_updated": self._count_navigation_updates(operation_results),
                "processing_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Routing operations completed: {successful_operations}/{len(operations)} operations successful"
            )

            return ExecutionResult(
                status=status,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None if overall_success else f"Failed operations: {failed_operations}"
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Routing tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format routing data for processing."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "disaster_location": {
                "latitude": alert_data.context.disaster_info.location.latitude,
                "longitude": alert_data.context.disaster_info.location.longitude,
                "address": alert_data.context.disaster_info.location.address
            },
            "affected_areas": [
                {
                    "center": {
                        "latitude": area.center.latitude,
                        "longitude": area.center.longitude
                    },
                    "radius_km": area.radius_km,
                    "area_name": area.area_name
                }
                for area in alert_data.context.disaster_info.affected_areas
            ],
            "existing_routes": [
                {
                    "route_id": route.route_id,
                    "start": {
                        "latitude": route.start_location.latitude,
                        "longitude": route.start_location.longitude
                    },
                    "end": {
                        "latitude": route.end_location.latitude,
                        "longitude": route.end_location.longitude
                    },
                    "distance_km": route.distance_km,
                    "estimated_time_minutes": route.estimated_time_minutes,
                    "capacity": route.capacity,
                    "current_load": route.current_load,
                    "utilization_rate": route.current_load / max(route.capacity, 1),
                    "geometry": route.route_geometry
                }
                for route in alert_data.context.evacuation_routes
            ],
            "safe_locations": [
                {
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "address": loc.address,
                    "administrative_area": loc.administrative_area
                }
                for loc in alert_data.context.geographical_context.safe_locations
            ],
            "blocked_routes": [
                {
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "reason": "disaster_impact"
                }
                for loc in alert_data.context.geographical_context.blocked_routes
            ],
            "affected_population": alert_data.context.affected_population.total_population,
            "vulnerable_population": alert_data.context.affected_population.vulnerable_population,
            "risk_metrics": {
                "evacuation_difficulty": alert_data.context.risk_assessment.evacuation_difficulty,
                "time_criticality": alert_data.context.risk_assessment.time_criticality,
                "traffic_congestion": alert_data.context.risk_assessment.traffic_congestion
            },
            "timestamp": alert_data.context.disaster_info.timestamp.isoformat()
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate routing tool configuration."""
        required_params = ["operations", "max_alternative_routes"]

        for param in required_params:
            if param not in tool_config.parameters:
                self.logger.error(f"Missing required parameter: {param}")
                return False

        # Validate operations
        operations = tool_config.parameters.get("operations", [])
        if not isinstance(operations, list) or not operations:
            self.logger.error("Invalid or empty operations configuration")
            return False

        # Validate each operation is supported
        for operation in operations:
            if operation not in self.routing_services:
                self.logger.error(
                    f"Unsupported routing operation: {operation}")
                return False

        # Validate max_alternative_routes
        max_routes = tool_config.parameters.get("max_alternative_routes", 0)
        if not isinstance(max_routes, int) or max_routes < 0:
            self.logger.error("Invalid max_alternative_routes parameter")
            return False

        return True

    def _select_operations_for_priority(self, priority: PriorityLevel, tool_config: ToolConfiguration) -> List[str]:
        """Select appropriate routing operations based on priority level."""
        all_operations = tool_config.parameters.get("operations", [])

        # Priority-based operation selection
        if priority == PriorityLevel.CRITICAL:
            # Use all available operations for critical situations
            return all_operations
        elif priority == PriorityLevel.HIGH:
            # Use high-priority operations
            preferred = ["primary_routing", "alternative_routing",
                         "real_time_updates", "navigation_integration"]
            return [op for op in preferred if op in all_operations] or all_operations
        elif priority == PriorityLevel.MEDIUM:
            # Use standard operations
            preferred = ["primary_routing",
                         "alternative_routing", "capacity_monitoring"]
            return [op for op in preferred if op in all_operations] or all_operations
        else:  # LOW priority
            # Use basic operations
            preferred = ["primary_routing", "capacity_monitoring"]
            return [op for op in preferred if op in all_operations] or all_operations[:1]

    async def _execute_routing_operation(self, operation: str, data: Dict[str, Any],
                                         tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute specific routing operation."""
        if operation not in self.routing_services:
            raise MCPToolError(f"Unsupported routing operation: {operation}")

        operation_func = self.routing_services[operation]
        return await operation_func(data, tool_config)

    async def _calculate_primary_routes(self, data: Dict[str, Any],
                                        tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Calculate and optimize primary evacuation routes."""
        try:
            # Analyze existing routes for optimization opportunities
            existing_routes = data["existing_routes"]
            optimized_routes = []

            for route in existing_routes:
                # Simulate route optimization based on current conditions
                optimized_route = await self._optimize_single_route(route, data)
                optimized_routes.append(optimized_route)

            # Calculate new routes if needed
            if len(optimized_routes) < 3:  # Ensure minimum route availability
                additional_routes = await self._calculate_additional_routes(data, 3 - len(optimized_routes))
                optimized_routes.extend(additional_routes)

            self.logger.info(
                f"Primary routing calculated: {len(optimized_routes)} routes optimized")

            return {
                "operation": "primary_routing",
                "success": True,
                "routes_optimized": len(existing_routes),
                "new_routes_calculated": max(0, 3 - len(existing_routes)),
                "total_routes": len(optimized_routes),
                "average_optimization_improvement": self._calculate_average_improvement(existing_routes, optimized_routes),
                "processing_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Primary routing calculation failed: {e}")
            return {
                "operation": "primary_routing",
                "success": False,
                "error": str(e)
            }

    async def _calculate_alternative_routes(self, data: Dict[str, Any],
                                            tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Calculate alternative evacuation routes."""
        try:
            max_alternatives = tool_config.parameters.get(
                "max_alternative_routes", 2)
            existing_routes = data["existing_routes"]

            alternative_routes = []

            # Generate alternative routes for each primary route
            # Limit to top 3 primary routes
            for primary_route in existing_routes[:3]:
                alternatives = await self._generate_route_alternatives(primary_route, data, max_alternatives)
                alternative_routes.extend(alternatives)

            # Remove duplicates and rank by efficiency
            unique_alternatives = self._deduplicate_routes(alternative_routes)
            ranked_alternatives = self._rank_routes_by_efficiency(
                unique_alternatives)

            self.logger.info(
                f"Alternative routing calculated: {len(ranked_alternatives)} alternative routes")

            return {
                "operation": "alternative_routing",
                "success": True,
                "alternatives_generated": len(alternative_routes),
                "unique_alternatives": len(unique_alternatives),
                "final_alternatives": len(ranked_alternatives),
                "average_efficiency_score": self._calculate_average_efficiency(ranked_alternatives),
                "processing_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Alternative routing calculation failed: {e}")
            return {
                "operation": "alternative_routing",
                "success": False,
                "error": str(e)
            }

    async def _update_routes_real_time(self, data: Dict[str, Any],
                                       tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Update routes with real-time traffic and condition data."""
        try:
            existing_routes = data["existing_routes"]
            updated_routes = []

            for route in existing_routes:
                # Simulate real-time data integration
                real_time_data = await self._fetch_real_time_route_data(route)
                updated_route = await self._apply_real_time_updates(route, real_time_data)
                updated_routes.append(updated_route)

            # Calculate impact of updates
            routes_with_changes = sum(
                1 for route in updated_routes if route.get("updated", False))
            average_time_change = self._calculate_average_time_change(
                existing_routes, updated_routes)

            self.logger.info(
                f"Real-time updates applied: {routes_with_changes}/{len(existing_routes)} routes updated")

            return {
                "operation": "real_time_updates",
                "success": True,
                "routes_processed": len(existing_routes),
                "routes_updated": routes_with_changes,
                "average_time_change_minutes": average_time_change,
                "update_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Real-time route updates failed: {e}")
            return {
                "operation": "real_time_updates",
                "success": False,
                "error": str(e)
            }

    async def _monitor_route_capacity(self, data: Dict[str, Any],
                                      tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Monitor and report on evacuation route capacity."""
        try:
            existing_routes = data["existing_routes"]
            capacity_reports = []

            for route in existing_routes:
                capacity_report = await self._analyze_route_capacity(route, data)
                capacity_reports.append(capacity_report)

            # Calculate overall capacity metrics
            total_capacity = sum(report["capacity"]
                                 for report in capacity_reports)
            total_current_load = sum(report["current_load"]
                                     for report in capacity_reports)
            overall_utilization = total_current_load / max(total_capacity, 1)

            # Identify capacity bottlenecks
            bottlenecks = [
                report for report in capacity_reports
                if report["utilization_rate"] > 0.8
            ]

            self.logger.info(
                f"Capacity monitoring completed: {len(bottlenecks)} bottlenecks identified")

            return {
                "operation": "capacity_monitoring",
                "success": True,
                "routes_monitored": len(existing_routes),
                "total_capacity": total_capacity,
                "current_utilization": overall_utilization,
                "bottlenecks_identified": len(bottlenecks),
                "capacity_reports": capacity_reports,
                "monitoring_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Capacity monitoring failed: {e}")
            return {
                "operation": "capacity_monitoring",
                "success": False,
                "error": str(e)
            }

    async def _integrate_with_navigation(self, data: Dict[str, Any],
                                         tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Integrate route information with navigation systems."""
        try:
            existing_routes = data["existing_routes"]
            navigation_systems = ["google_maps",
                                  "apple_maps", "waze", "emergency_nav"]

            integration_results = []
            successful_integrations = 0

            for nav_system in navigation_systems:
                try:
                    integration_result = await self._integrate_with_nav_system(
                        nav_system, existing_routes, data
                    )
                    integration_results.append(integration_result)

                    if integration_result.get("success", False):
                        successful_integrations += 1

                except Exception as e:
                    self.logger.error(
                        f"Navigation integration failed for {nav_system}: {e}")
                    integration_results.append({
                        "navigation_system": nav_system,
                        "success": False,
                        "error": str(e)
                    })

            self.logger.info(
                f"Navigation integration completed: {successful_integrations}/{len(navigation_systems)} systems updated")

            return {
                "operation": "navigation_integration",
                "success": successful_integrations > 0,
                "systems_attempted": len(navigation_systems),
                "successful_integrations": successful_integrations,
                "integration_results": integration_results,
                "routes_distributed": len(existing_routes),
                "integration_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Navigation integration failed: {e}")
            return {
                "operation": "navigation_integration",
                "success": False,
                "error": str(e)
            }

    async def _optimize_single_route(self, route: Dict[str, Any], context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a single route based on current conditions."""
        # Simulate route optimization
        await asyncio.sleep(0.02)  # Simulate processing time

        # Apply optimization factors
        optimization_factor = 0.9  # 10% improvement
        risk_factor = context_data["risk_metrics"]["traffic_congestion"]

        optimized_route = route.copy()
        optimized_route["estimated_time_minutes"] = int(
            route["estimated_time_minutes"] * optimization_factor * (1 + risk_factor * 0.2))
        optimized_route["optimization_applied"] = True
        optimized_route["optimization_factor"] = optimization_factor

        return optimized_route

    async def _calculate_additional_routes(self, data: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """Calculate additional evacuation routes."""
        additional_routes = []

        for i in range(count):
            # Simulate route calculation
            await asyncio.sleep(0.05)

            route = {
                "route_id": f"additional_route_{i+1}",
                "start": data["disaster_location"],
                "end": data["safe_locations"][i % len(data["safe_locations"])] if data["safe_locations"] else data["disaster_location"],
                "distance_km": 5.0 + i * 2.0,
                "estimated_time_minutes": 15 + i * 5,
                "capacity": 500,
                "current_load": 0,
                "utilization_rate": 0.0,
                "route_type": "additional"
            }
            additional_routes.append(route)

        return additional_routes

    async def _generate_route_alternatives(self, primary_route: Dict[str, Any],
                                           context_data: Dict[str, Any], max_alternatives: int) -> List[Dict[str, Any]]:
        """Generate alternative routes for a primary route."""
        alternatives = []

        for i in range(max_alternatives):
            # Simulate alternative route generation
            await asyncio.sleep(0.03)

            alternative = {
                "route_id": f"{primary_route['route_id']}_alt_{i+1}",
                "start": primary_route["start"],
                "end": primary_route["end"],
                "distance_km": primary_route["distance_km"] * (1.1 + i * 0.1),
                "estimated_time_minutes": int(primary_route["estimated_time_minutes"] * (1.05 + i * 0.05)),
                "capacity": primary_route["capacity"],
                "current_load": 0,
                "utilization_rate": 0.0,
                "route_type": "alternative",
                "primary_route_id": primary_route["route_id"]
            }
            alternatives.append(alternative)

        return alternatives

    async def _fetch_real_time_route_data(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch real-time data for a route."""
        # Simulate real-time data fetch
        await asyncio.sleep(0.01)

        return {
            "traffic_factor": 1.2,  # 20% slower due to traffic
            "road_conditions": "normal",
            "incidents": [],
            "weather_impact": 1.0,
            "last_updated": datetime.now().isoformat()
        }

    async def _apply_real_time_updates(self, route: Dict[str, Any], real_time_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply real-time updates to a route."""
        updated_route = route.copy()

        # Apply traffic factor
        traffic_factor = real_time_data.get("traffic_factor", 1.0)
        updated_route["estimated_time_minutes"] = int(
            route["estimated_time_minutes"] * traffic_factor)

        # Mark as updated if there's a significant change
        time_change = abs(
            updated_route["estimated_time_minutes"] - route["estimated_time_minutes"])
        # More than 2 minutes change
        updated_route["updated"] = time_change > 2
        updated_route["real_time_data"] = real_time_data

        return updated_route

    async def _analyze_route_capacity(self, route: Dict[str, Any], context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze capacity for a single route."""
        # Simulate capacity analysis
        await asyncio.sleep(0.01)

        return {
            "route_id": route["route_id"],
            "capacity": route["capacity"],
            "current_load": route["current_load"],
            "utilization_rate": route["utilization_rate"],
            # 30% may use this route
            "projected_demand": int(context_data["affected_population"] * 0.3),
            "capacity_status": "available" if route["utilization_rate"] < 0.8 else "near_capacity",
            "estimated_wait_time": max(0, (route["current_load"] - route["capacity"]) * 2) if route["current_load"] > route["capacity"] else 0
        }

    async def _integrate_with_nav_system(self, nav_system: str, routes: List[Dict[str, Any]],
                                         context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate routes with a specific navigation system."""
        # Simulate navigation system integration
        await asyncio.sleep(0.05)

        return {
            "navigation_system": nav_system,
            "success": True,
            "routes_uploaded": len(routes),
            "integration_method": "api_push",
            "estimated_propagation_time_minutes": 5,
            "coverage_area_km2": 100,
            "integration_timestamp": datetime.now().isoformat()
        }

    def _deduplicate_routes(self, routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate routes based on start/end points."""
        seen_routes = set()
        unique_routes = []

        for route in routes:
            route_key = (
                route["start"]["latitude"],
                route["start"]["longitude"],
                route["end"]["latitude"],
                route["end"]["longitude"]
            )

            if route_key not in seen_routes:
                seen_routes.add(route_key)
                unique_routes.append(route)

        return unique_routes

    def _rank_routes_by_efficiency(self, routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank routes by efficiency (time/distance ratio)."""
        for route in routes:
            # Calculate efficiency score (lower is better)
            route["efficiency_score"] = route["estimated_time_minutes"] / \
                max(route["distance_km"], 0.1)

        # Sort by efficiency score
        return sorted(routes, key=lambda r: r["efficiency_score"])

    def _calculate_average_improvement(self, original_routes: List[Dict[str, Any]],
                                       optimized_routes: List[Dict[str, Any]]) -> float:
        """Calculate average improvement from optimization."""
        if not original_routes or not optimized_routes:
            return 0.0

        improvements = []
        for orig, opt in zip(original_routes, optimized_routes):
            if orig["estimated_time_minutes"] > 0:
                improvement = (orig["estimated_time_minutes"] -
                               opt["estimated_time_minutes"]) / orig["estimated_time_minutes"]
                improvements.append(improvement)

        return sum(improvements) / len(improvements) if improvements else 0.0

    def _calculate_average_efficiency(self, routes: List[Dict[str, Any]]) -> float:
        """Calculate average efficiency score of routes."""
        if not routes:
            return 0.0

        efficiency_scores = [route.get("efficiency_score", 0)
                             for route in routes]
        return sum(efficiency_scores) / len(efficiency_scores)

    def _calculate_average_time_change(self, original_routes: List[Dict[str, Any]],
                                       updated_routes: List[Dict[str, Any]]) -> float:
        """Calculate average time change from real-time updates."""
        if not original_routes or not updated_routes:
            return 0.0

        time_changes = []
        for orig, updated in zip(original_routes, updated_routes):
            time_change = updated["estimated_time_minutes"] - \
                orig["estimated_time_minutes"]
            time_changes.append(time_change)

        return sum(time_changes) / len(time_changes) if time_changes else 0.0

    def _count_alternative_routes(self, operation_results: List[Dict[str, Any]]) -> int:
        """Count alternative routes generated from operation results."""
        for result in operation_results:
            if result.get("operation") == "alternative_routing" and result.get("success"):
                return result.get("final_alternatives", 0)
        return 0

    def _count_navigation_updates(self, operation_results: List[Dict[str, Any]]) -> int:
        """Count navigation systems updated from operation results."""
        for result in operation_results:
            if result.get("operation") == "navigation_integration" and result.get("success"):
                return result.get("successful_integrations", 0)
        return 0

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
