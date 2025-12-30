"""
Concrete implementation of MCP Context Tool for disaster context management.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx

from agentic_disaster_response.mcp_integration import MCPTool, AlertData, ExecutionResult, ExecutionStatus
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, ToolConfiguration
from agentic_disaster_response.models.alert_priority import PriorityLevel
from agentic_disaster_response.core.exceptions import MCPToolError


class ContextMCPTool(MCPTool):
    """
    Concrete implementation of MCP Context Tool for disaster context management.

    This tool handles:
    - Real-time context data collection
    - Situational awareness updates
    - Context data validation and enrichment
    - Context sharing with external systems
    - Historical context analysis
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=60.0)
        self.context_services = {
            "data_collection": self._collect_context_data,
            "situational_awareness": self._update_situational_awareness,
            "data_validation": self._validate_context_data,
            "context_sharing": self._share_context_data,
            "historical_analysis": self._analyze_historical_context
        }

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute context management operations."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing context tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for context tool {self.config.tool_name}")

            # Format data for this tool
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Determine context operations based on priority
            operations = self._select_operations_for_priority(
                alert_data.priority.level, tool_config)

            # Execute context operations
            operation_results = []
            successful_operations = 0
            failed_operations = 0

            for operation in operations:
                try:
                    operation_result = await self._execute_context_operation(
                        operation, formatted_data, tool_config
                    )
                    operation_results.append(operation_result)

                    if operation_result.get("success", False):
                        successful_operations += 1
                    else:
                        failed_operations += 1

                except Exception as e:
                    self.logger.error(
                        f"Context operation {operation} failed: {e}")
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
                "context_completeness": formatted_data["context_completeness"],
                "data_sources_accessed": self._count_data_sources(operation_results),
                "context_updates_shared": self._count_context_shares(operation_results),
                "processing_timestamp": datetime.now().isoformat()
            }

            self.logger.info(
                f"Context operations completed: {successful_operations}/{len(operations)} operations successful"
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
            self.logger.error(f"Context tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format context data for processing."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "disaster_info": {
                "disaster_id": alert_data.context.disaster_info.disaster_id,
                "disaster_type": alert_data.context.disaster_info.disaster_type.value,
                "severity": alert_data.context.disaster_info.severity.value,
                "location": {
                    "latitude": alert_data.context.disaster_info.location.latitude,
                    "longitude": alert_data.context.disaster_info.location.longitude,
                    "address": alert_data.context.disaster_info.location.address,
                    "administrative_area": alert_data.context.disaster_info.location.administrative_area
                },
                "timestamp": alert_data.context.disaster_info.timestamp.isoformat(),
                "description": alert_data.context.disaster_info.description,
                "source": alert_data.context.disaster_info.source
            },
            "context_completeness": alert_data.context.context_completeness,
            "missing_data_indicators": alert_data.context.missing_data_indicators,
            "geographical_context": {
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
                "safe_locations": [
                    {
                        "latitude": loc.latitude,
                        "longitude": loc.longitude,
                        "address": loc.address
                    }
                    for loc in alert_data.context.geographical_context.safe_locations
                ],
                "blocked_routes_count": len(alert_data.context.geographical_context.blocked_routes),
                "accessible_routes_count": len(alert_data.context.geographical_context.accessible_routes)
            },
            "population_data": {
                "total_population": alert_data.context.affected_population.total_population,
                "vulnerable_population": alert_data.context.affected_population.vulnerable_population,
                "current_occupancy": alert_data.context.affected_population.current_occupancy,
                "population_density_per_km2": alert_data.context.affected_population.population_density_per_km2
            },
            "resource_inventory": {
                "available_shelters": alert_data.context.available_resources.available_shelters,
                "shelter_capacity": alert_data.context.available_resources.shelter_capacity,
                "medical_facilities": alert_data.context.available_resources.medical_facilities,
                "emergency_vehicles": alert_data.context.available_resources.emergency_vehicles,
                "communication_systems": alert_data.context.available_resources.communication_systems,
                "backup_power_systems": alert_data.context.available_resources.backup_power_systems
            },
            "risk_assessment": {
                "overall_risk_score": alert_data.context.risk_assessment.overall_risk_score,
                "evacuation_difficulty": alert_data.context.risk_assessment.evacuation_difficulty,
                "time_criticality": alert_data.context.risk_assessment.time_criticality,
                "resource_availability": alert_data.context.risk_assessment.resource_availability,
                "weather_impact": alert_data.context.risk_assessment.weather_impact,
                "traffic_congestion": alert_data.context.risk_assessment.traffic_congestion
            },
            "evacuation_routes": [
                {
                    "route_id": route.route_id,
                    "distance_km": route.distance_km,
                    "estimated_time_minutes": route.estimated_time_minutes,
                    "capacity": route.capacity,
                    "current_load": route.current_load,
                    "utilization_rate": route.current_load / max(route.capacity, 1)
                }
                for route in alert_data.context.evacuation_routes
            ]
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate context tool configuration."""
        required_params = ["operations", "data_sources"]

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
            if operation not in self.context_services:
                self.logger.error(
                    f"Unsupported context operation: {operation}")
                return False

        # Validate data sources
        data_sources = tool_config.parameters.get("data_sources", [])
        if not isinstance(data_sources, list):
            self.logger.error("Invalid data_sources configuration")
            return False

        return True

    def _select_operations_for_priority(self, priority: PriorityLevel, tool_config: ToolConfiguration) -> List[str]:
        """Select appropriate context operations based on priority level."""
        all_operations = tool_config.parameters.get("operations", [])

        # Priority-based operation selection
        if priority == PriorityLevel.CRITICAL:
            # Use all available operations for critical situations
            return all_operations
        elif priority == PriorityLevel.HIGH:
            # Use high-priority operations
            preferred = ["data_collection", "situational_awareness",
                         "data_validation", "context_sharing"]
            return [op for op in preferred if op in all_operations] or all_operations
        elif priority == PriorityLevel.MEDIUM:
            # Use standard operations
            preferred = ["data_collection",
                         "data_validation", "context_sharing"]
            return [op for op in preferred if op in all_operations] or all_operations
        else:  # LOW priority
            # Use basic operations
            preferred = ["data_collection", "data_validation"]
            return [op for op in preferred if op in all_operations] or all_operations[:1]

    async def _execute_context_operation(self, operation: str, data: Dict[str, Any],
                                         tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Execute specific context operation."""
        if operation not in self.context_services:
            raise MCPToolError(f"Unsupported context operation: {operation}")

        operation_func = self.context_services[operation]
        return await operation_func(data, tool_config)

    async def _collect_context_data(self, data: Dict[str, Any],
                                    tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Collect additional context data from external sources."""
        try:
            data_sources = tool_config.parameters.get("data_sources", [])
            collected_data = {}
            successful_sources = 0
            failed_sources = 0

            for source in data_sources:
                try:
                    source_data = await self._collect_from_data_source(source, data)
                    collected_data[source] = source_data
                    successful_sources += 1
                except Exception as e:
                    self.logger.error(
                        f"Data collection from {source} failed: {e}")
                    collected_data[source] = {"error": str(e)}
                    failed_sources += 1

            # Analyze data completeness improvement
            original_completeness = data["context_completeness"]
            improved_completeness = min(
                1.0, original_completeness + (successful_sources * 0.1))

            self.logger.info(
                f"Context data collection completed: {successful_sources}/{len(data_sources)} sources successful")

            return {
                "operation": "data_collection",
                "success": successful_sources > 0,
                "sources_attempted": len(data_sources),
                "successful_sources": successful_sources,
                "failed_sources": failed_sources,
                "original_completeness": original_completeness,
                "improved_completeness": improved_completeness,
                "completeness_improvement": improved_completeness - original_completeness,
                "collected_data": collected_data,
                "collection_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Context data collection failed: {e}")
            return {
                "operation": "data_collection",
                "success": False,
                "error": str(e)
            }

    async def _update_situational_awareness(self, data: Dict[str, Any],
                                            tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Update situational awareness information."""
        try:
            # Generate situational awareness updates
            awareness_updates = await self._generate_awareness_updates(data)

            # Calculate situational metrics
            situation_metrics = await self._calculate_situation_metrics(data)

            # Generate recommendations
            recommendations = await self._generate_situation_recommendations(data, situation_metrics)

            # Create situational awareness report
            awareness_report = {
                "disaster_status": self._assess_disaster_status(data),
                "population_impact": self._assess_population_impact(data),
                "resource_status": self._assess_resource_status(data),
                "evacuation_status": self._assess_evacuation_status(data),
                "risk_level": self._assess_current_risk_level(data),
                "time_criticality": data["risk_assessment"]["time_criticality"],
                "situation_trends": await self._analyze_situation_trends(data)
            }

            self.logger.info("Situational awareness updated successfully")

            return {
                "operation": "situational_awareness",
                "success": True,
                "awareness_updates": awareness_updates,
                "situation_metrics": situation_metrics,
                "recommendations": recommendations,
                "awareness_report": awareness_report,
                "update_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Situational awareness update failed: {e}")
            return {
                "operation": "situational_awareness",
                "success": False,
                "error": str(e)
            }

    async def _validate_context_data(self, data: Dict[str, Any],
                                     tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Validate and verify context data accuracy."""
        try:
            validation_results = {}

            # Validate disaster information
            disaster_validation = await self._validate_disaster_info(data["disaster_info"])
            validation_results["disaster_info"] = disaster_validation

            # Validate geographical context
            geo_validation = await self._validate_geographical_context(data["geographical_context"])
            validation_results["geographical_context"] = geo_validation

            # Validate population data
            population_validation = await self._validate_population_data(data["population_data"])
            validation_results["population_data"] = population_validation

            # Validate resource inventory
            resource_validation = await self._validate_resource_inventory(data["resource_inventory"])
            validation_results["resource_inventory"] = resource_validation

            # Validate risk assessment
            risk_validation = await self._validate_risk_assessment(data["risk_assessment"])
            validation_results["risk_assessment"] = risk_validation

            # Calculate overall validation score
            validation_scores = [result["validation_score"]
                                 for result in validation_results.values()]
            overall_validation_score = sum(
                validation_scores) / len(validation_scores)

            # Identify validation issues
            validation_issues = []
            for category, result in validation_results.items():
                if result["validation_score"] < 0.8:
                    validation_issues.extend(result.get("issues", []))

            self.logger.info(
                f"Context data validation completed: overall score {overall_validation_score:.2f}")

            return {
                "operation": "data_validation",
                "success": True,
                "overall_validation_score": overall_validation_score,
                "validation_results": validation_results,
                "validation_issues": validation_issues,
                "data_quality": "high" if overall_validation_score > 0.8 else "medium" if overall_validation_score > 0.6 else "low",
                "validation_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Context data validation failed: {e}")
            return {
                "operation": "data_validation",
                "success": False,
                "error": str(e)
            }

    async def _share_context_data(self, data: Dict[str, Any],
                                  tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Share context data with external systems."""
        try:
            sharing_targets = tool_config.parameters.get("sharing_targets", [
                "emergency_services", "local_government", "media_outlets", "public_systems"
            ])

            sharing_results = []
            successful_shares = 0
            failed_shares = 0

            for target in sharing_targets:
                try:
                    share_result = await self._share_with_target(target, data)
                    sharing_results.append(share_result)

                    if share_result.get("success", False):
                        successful_shares += 1
                    else:
                        failed_shares += 1

                except Exception as e:
                    self.logger.error(
                        f"Context sharing with {target} failed: {e}")
                    sharing_results.append({
                        "target": target,
                        "success": False,
                        "error": str(e)
                    })
                    failed_shares += 1

            # Calculate sharing metrics
            total_recipients = sum(result.get("recipients_reached", 0)
                                   for result in sharing_results)

            self.logger.info(
                f"Context sharing completed: {successful_shares}/{len(sharing_targets)} targets successful")

            return {
                "operation": "context_sharing",
                "success": successful_shares > 0,
                "targets_attempted": len(sharing_targets),
                "successful_shares": successful_shares,
                "failed_shares": failed_shares,
                "total_recipients": total_recipients,
                "sharing_results": sharing_results,
                "sharing_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Context sharing failed: {e}")
            return {
                "operation": "context_sharing",
                "success": False,
                "error": str(e)
            }

    async def _analyze_historical_context(self, data: Dict[str, Any],
                                          tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Analyze historical context for similar disasters."""
        try:
            # Find similar historical disasters
            similar_disasters = await self._find_similar_disasters(data)

            # Analyze historical patterns
            historical_patterns = await self._analyze_historical_patterns(similar_disasters)

            # Generate insights from historical data
            historical_insights = await self._generate_historical_insights(data, similar_disasters, historical_patterns)

            # Calculate confidence in historical analysis
            analysis_confidence = self._calculate_historical_confidence(
                similar_disasters, historical_patterns)

            self.logger.info(
                f"Historical context analysis completed: {len(similar_disasters)} similar disasters analyzed")

            return {
                "operation": "historical_analysis",
                "success": True,
                "similar_disasters_found": len(similar_disasters),
                "historical_patterns": historical_patterns,
                "historical_insights": historical_insights,
                "analysis_confidence": analysis_confidence,
                "similar_disasters": similar_disasters,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Historical context analysis failed: {e}")
            return {
                "operation": "historical_analysis",
                "success": False,
                "error": str(e)
            }

    async def _collect_from_data_source(self, source: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data from a specific external source."""
        # Simulate data collection from various sources
        await asyncio.sleep(0.1)  # Simulate network delay

        source_data = {
            "weather_service": {
                "current_weather": "clear",
                "forecast": "stable",
                "wind_speed_kmh": 15,
                "temperature_c": 22,
                "humidity_percent": 65
            },
            "traffic_service": {
                "congestion_level": "moderate",
                "blocked_roads": 2,
                "average_speed_kmh": 35,
                "incidents": 1
            },
            "social_media": {
                "mentions": 150,
                "sentiment": "concerned",
                "trending_topics": ["evacuation", "safety", "emergency"]
            },
            "sensor_network": {
                "air_quality": "good",
                "noise_level": "elevated",
                "radiation_level": "normal"
            }
        }

        return source_data.get(source, {"status": "no_data_available"})

    async def _generate_awareness_updates(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate situational awareness updates."""
        updates = []

        # Population impact update
        updates.append({
            "category": "population_impact",
            "severity": "high" if data["population_data"]["total_population"] > 5000 else "medium",
            "message": f"{data['population_data']['total_population']:,} people affected",
            "timestamp": datetime.now().isoformat()
        })

        # Resource status update
        updates.append({
            "category": "resource_status",
            "severity": "medium",
            "message": f"{data['resource_inventory']['available_shelters']} shelters available with capacity for {data['resource_inventory']['shelter_capacity']:,}",
            "timestamp": datetime.now().isoformat()
        })

        # Evacuation status update
        updates.append({
            "category": "evacuation_status",
            "severity": "high" if len(data["evacuation_routes"]) < 2 else "medium",
            "message": f"{len(data['evacuation_routes'])} evacuation routes available",
            "timestamp": datetime.now().isoformat()
        })

        return updates

    async def _calculate_situation_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key situational metrics."""
        return {
            "population_at_risk_ratio": data["population_data"]["vulnerable_population"] / max(data["population_data"]["total_population"], 1),
            "resource_adequacy_ratio": data["resource_inventory"]["shelter_capacity"] / max(data["population_data"]["total_population"], 1),
            "evacuation_capacity_ratio": sum(route["capacity"] for route in data["evacuation_routes"]) / max(data["population_data"]["total_population"], 1),
            "time_pressure_index": data["risk_assessment"]["time_criticality"],
            "overall_preparedness_score": (
                data["context_completeness"] * 0.3 +
                (1 - data["risk_assessment"]["evacuation_difficulty"]) * 0.3 +
                data["risk_assessment"]["resource_availability"] * 0.4
            )
        }

    async def _generate_situation_recommendations(self, data: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on situation analysis."""
        recommendations = []

        if metrics["population_at_risk_ratio"] > 0.3:
            recommendations.append(
                "Prioritize evacuation of vulnerable populations")

        if metrics["resource_adequacy_ratio"] < 1.0:
            recommendations.append(
                "Request additional shelter resources from neighboring areas")

        if metrics["evacuation_capacity_ratio"] < 0.8:
            recommendations.append(
                "Activate additional evacuation routes or transportation")

        if metrics["time_pressure_index"] > 0.7:
            recommendations.append(
                "Accelerate evacuation timeline due to high time criticality")

        if metrics["overall_preparedness_score"] < 0.6:
            recommendations.append(
                "Implement emergency preparedness measures immediately")

        return recommendations

    def _assess_disaster_status(self, data: Dict[str, Any]) -> str:
        """Assess current disaster status."""
        severity = data["disaster_info"]["severity"]
        time_criticality = data["risk_assessment"]["time_criticality"]

        if severity == "critical" or time_criticality > 0.8:
            return "critical"
        elif severity == "high" or time_criticality > 0.6:
            return "high"
        elif severity == "medium" or time_criticality > 0.4:
            return "medium"
        else:
            return "low"

    def _assess_population_impact(self, data: Dict[str, Any]) -> str:
        """Assess population impact level."""
        total_pop = data["population_data"]["total_population"]
        vulnerable_ratio = data["population_data"]["vulnerable_population"] / \
            max(total_pop, 1)

        if total_pop > 10000 or vulnerable_ratio > 0.4:
            return "severe"
        elif total_pop > 5000 or vulnerable_ratio > 0.2:
            return "moderate"
        else:
            return "limited"

    def _assess_resource_status(self, data: Dict[str, Any]) -> str:
        """Assess resource availability status."""
        resources = data["resource_inventory"]
        total_pop = data["population_data"]["total_population"]

        shelter_ratio = resources["shelter_capacity"] / max(total_pop, 1)

        if shelter_ratio >= 1.0 and resources["medical_facilities"] >= 2:
            return "adequate"
        elif shelter_ratio >= 0.7 and resources["medical_facilities"] >= 1:
            return "limited"
        else:
            return "insufficient"

    def _assess_evacuation_status(self, data: Dict[str, Any]) -> str:
        """Assess evacuation readiness status."""
        routes = data["evacuation_routes"]
        total_capacity = sum(route["capacity"] for route in routes)
        total_pop = data["population_data"]["total_population"]

        capacity_ratio = total_capacity / max(total_pop, 1)

        if len(routes) >= 3 and capacity_ratio >= 1.0:
            return "ready"
        elif len(routes) >= 2 and capacity_ratio >= 0.7:
            return "limited"
        else:
            return "inadequate"

    def _assess_current_risk_level(self, data: Dict[str, Any]) -> str:
        """Assess current overall risk level."""
        risk_score = data["risk_assessment"]["overall_risk_score"]

        if risk_score >= 0.8:
            return "extreme"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "moderate"
        else:
            return "low"

    async def _analyze_situation_trends(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in the current situation."""
        # Simulate trend analysis
        await asyncio.sleep(0.05)

        return {
            "risk_trend": "increasing" if data["risk_assessment"]["time_criticality"] > 0.6 else "stable",
            "population_movement": "evacuating" if len(data["evacuation_routes"]) > 0 else "stationary",
            "resource_utilization": "increasing",
            "situation_stability": "deteriorating" if data["risk_assessment"]["overall_risk_score"] > 0.7 else "stable"
        }

    async def _validate_disaster_info(self, disaster_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate disaster information."""
        issues = []
        score = 1.0

        # Check required fields
        required_fields = ["disaster_id", "disaster_type",
                           "severity", "location", "timestamp"]
        for field in required_fields:
            if not disaster_info.get(field):
                issues.append(f"Missing {field}")
                score -= 0.2

        # Validate location coordinates
        location = disaster_info.get("location", {})
        if not (-90 <= location.get("latitude", 0) <= 90):
            issues.append("Invalid latitude")
            score -= 0.1
        if not (-180 <= location.get("longitude", 0) <= 180):
            issues.append("Invalid longitude")
            score -= 0.1

        return {
            "validation_score": max(0.0, score),
            "issues": issues,
            "validated_fields": len(required_fields) - len([i for i in issues if "Missing" in i])
        }

    async def _validate_geographical_context(self, geo_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate geographical context data."""
        issues = []
        score = 1.0

        # Check affected areas
        affected_areas = geo_context.get("affected_areas", [])
        if not affected_areas:
            issues.append("No affected areas defined")
            score -= 0.3

        # Check safe locations
        safe_locations = geo_context.get("safe_locations", [])
        if not safe_locations:
            issues.append("No safe locations identified")
            score -= 0.2

        return {
            "validation_score": max(0.0, score),
            "issues": issues,
            "affected_areas_count": len(affected_areas),
            "safe_locations_count": len(safe_locations)
        }

    async def _validate_population_data(self, population_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate population data."""
        issues = []
        score = 1.0

        total_pop = population_data.get("total_population", 0)
        vulnerable_pop = population_data.get("vulnerable_population", 0)

        if total_pop <= 0:
            issues.append("Invalid total population")
            score -= 0.4

        if vulnerable_pop > total_pop:
            issues.append("Vulnerable population exceeds total population")
            score -= 0.3

        if vulnerable_pop < 0:
            issues.append("Negative vulnerable population")
            score -= 0.2

        return {
            "validation_score": max(0.0, score),
            "issues": issues,
            "population_ratio_valid": vulnerable_pop <= total_pop
        }

    async def _validate_resource_inventory(self, resource_inventory: Dict[str, Any]) -> Dict[str, Any]:
        """Validate resource inventory data."""
        issues = []
        score = 1.0

        # Check for negative values
        for resource, count in resource_inventory.items():
            if isinstance(count, (int, float)) and count < 0:
                issues.append(f"Negative {resource} count")
                score -= 0.1

        # Check shelter capacity vs shelters
        shelters = resource_inventory.get("available_shelters", 0)
        capacity = resource_inventory.get("shelter_capacity", 0)

        if shelters > 0 and capacity == 0:
            issues.append("Shelters available but no capacity specified")
            score -= 0.2

        return {
            "validation_score": max(0.0, score),
            "issues": issues,
            "resource_consistency": len(issues) == 0
        }

    async def _validate_risk_assessment(self, risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Validate risk assessment data."""
        issues = []
        score = 1.0

        # Check score ranges (should be 0-1)
        risk_fields = ["overall_risk_score", "evacuation_difficulty",
                       "time_criticality", "resource_availability"]

        for field in risk_fields:
            value = risk_assessment.get(field, 0)
            if not (0 <= value <= 1):
                issues.append(f"Invalid {field} range (should be 0-1)")
                score -= 0.2

        return {
            "validation_score": max(0.0, score),
            "issues": issues,
            "valid_risk_fields": len(risk_fields) - len([i for i in issues if "Invalid" in i])
        }

    async def _share_with_target(self, target: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Share context data with a specific target system."""
        # Simulate sharing with different target systems
        await asyncio.sleep(0.05)

        target_configs = {
            "emergency_services": {
                "recipients_reached": 50,
                "data_format": "emergency_protocol",
                "delivery_method": "secure_api"
            },
            "local_government": {
                "recipients_reached": 25,
                "data_format": "government_standard",
                "delivery_method": "official_channels"
            },
            "media_outlets": {
                "recipients_reached": 100,
                "data_format": "public_summary",
                "delivery_method": "press_release"
            },
            "public_systems": {
                "recipients_reached": 1000,
                "data_format": "public_alert",
                "delivery_method": "broadcast"
            }
        }

        config = target_configs.get(target, {
                                    "recipients_reached": 10, "data_format": "standard", "delivery_method": "api"})

        return {
            "target": target,
            "success": True,
            "recipients_reached": config["recipients_reached"],
            "data_format": config["data_format"],
            "delivery_method": config["delivery_method"],
            "sharing_timestamp": datetime.now().isoformat()
        }

    async def _find_similar_disasters(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar historical disasters."""
        # Simulate historical disaster lookup
        await asyncio.sleep(0.1)

        # Mock historical disasters
        similar_disasters = [
            {
                "disaster_id": "hist_001",
                "disaster_type": data["disaster_info"]["disaster_type"],
                "severity": "high",
                "affected_population": 8000,
                "outcome": "successful_evacuation",
                "lessons_learned": ["Early evacuation key", "Multiple routes essential"]
            },
            {
                "disaster_id": "hist_002",
                "disaster_type": data["disaster_info"]["disaster_type"],
                "severity": "medium",
                "affected_population": 3000,
                "outcome": "partial_evacuation",
                "lessons_learned": ["Communication critical", "Resource coordination needed"]
            }
        ]

        return similar_disasters

    async def _analyze_historical_patterns(self, similar_disasters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns from historical disasters."""
        if not similar_disasters:
            return {"patterns": [], "confidence": 0.0}

        patterns = {
            "success_factors": ["early_warning", "multiple_evacuation_routes", "clear_communication"],
            "common_challenges": ["traffic_congestion", "resource_shortages", "communication_failures"],
            "average_evacuation_time": 120,  # minutes
            "success_rate": 0.8
        }

        return patterns

    async def _generate_historical_insights(self, current_data: Dict[str, Any],
                                            similar_disasters: List[Dict[str, Any]],
                                            patterns: Dict[str, Any]) -> List[str]:
        """Generate insights based on historical analysis."""
        insights = []

        if len(similar_disasters) > 0:
            insights.append(
                f"Based on {len(similar_disasters)} similar disasters, early evacuation is critical")

        if patterns.get("success_rate", 0) > 0.7:
            insights.append(
                "Historical data shows high success rate for similar disasters")

        current_routes = len(current_data.get("evacuation_routes", []))
        if current_routes < 3:
            insights.append(
                "Historical patterns suggest having at least 3 evacuation routes improves outcomes")

        return insights

    def _calculate_historical_confidence(self, similar_disasters: List[Dict[str, Any]],
                                         patterns: Dict[str, Any]) -> float:
        """Calculate confidence in historical analysis."""
        if not similar_disasters:
            return 0.0

        # Base confidence on number of similar disasters and pattern consistency
        base_confidence = min(0.9, len(similar_disasters) * 0.2)
        pattern_confidence = patterns.get("success_rate", 0.5)

        return (base_confidence + pattern_confidence) / 2

    def _count_data_sources(self, operation_results: List[Dict[str, Any]]) -> int:
        """Count data sources accessed from operation results."""
        for result in operation_results:
            if result.get("operation") == "data_collection" and result.get("success"):
                return result.get("successful_sources", 0)
        return 0

    def _count_context_shares(self, operation_results: List[Dict[str, Any]]) -> int:
        """Count context shares completed from operation results."""
        for result in operation_results:
            if result.get("operation") == "context_sharing" and result.get("success"):
                return result.get("successful_shares", 0)
        return 0

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
