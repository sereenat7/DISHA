"""
Context Builder component for enriching disaster data with geographical context.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models.disaster_data import DisasterData, DisasterType, SeverityLevel
from .models.location import Location
from .models.context import (
    StructuredContext, GeographicalContext, EvacuationRoute,
    PopulationData, ResourceInventory, RiskMetrics, EnrichedContext
)
from Backend.evacuation_system.main import find_evacuation_routes, get_safe_locations


logger = logging.getLogger(__name__)


class ContextValidationError(Exception):
    """Raised when context validation fails."""
    pass


class ContextBuilder:
    """
    Builds comprehensive contextual understanding of disaster events by enriching
    disaster data with geographical context, evacuation routes, and risk assessment.
    """

    def __init__(self, search_radius_km: float = 10.0, max_routes_per_category: int = 3):
        """
        Initialize the Context Builder.

        Args:
            search_radius_km: Radius for searching safe locations and routes
            max_routes_per_category: Maximum evacuation routes per safety category
        """
        self.search_radius_km = search_radius_km
        self.max_routes_per_category = max_routes_per_category
        logger.info(
            f"ContextBuilder initialized with radius {search_radius_km}km")

    async def build_context(self, disaster_data: DisasterData) -> StructuredContext:
        """
        Build comprehensive context from disaster data by enriching with geographical
        context and evacuation route information.

        Args:
            disaster_data: Core disaster information

        Returns:
            StructuredContext: Enriched context data for decision-making

        Raises:
            ValueError: If disaster_data is invalid
            Exception: If context building fails critically
        """
        if not disaster_data:
            raise ValueError("Disaster data cannot be None")

        logger.info(
            f"Building context for disaster {disaster_data.disaster_id}")

        try:
            # Build geographical context with safe locations
            geographical_context = await self._build_geographical_context(disaster_data)

            # Get evacuation routes from existing system
            evacuation_routes = await self._get_evacuation_routes(disaster_data)

            # Assess population impact
            population_data = self._assess_population_impact(disaster_data)

            # Inventory available resources
            resource_inventory = self._inventory_resources(
                disaster_data, geographical_context)

            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(
                disaster_data, geographical_context, evacuation_routes, population_data
            )

            # Determine context completeness
            completeness, missing_indicators = self._assess_completeness(
                geographical_context, evacuation_routes, population_data, resource_inventory
            )

            context = StructuredContext(
                disaster_info=disaster_data,
                geographical_context=geographical_context,
                evacuation_routes=evacuation_routes,
                affected_population=population_data,
                available_resources=resource_inventory,
                risk_assessment=risk_metrics,
                context_completeness=completeness,
                missing_data_indicators=missing_indicators
            )

            # Validate the constructed context
            self._validate_context(context)

            # Handle partial context scenarios if needed
            if context.context_completeness < 0.5:
                context = self._handle_partial_context(context)

            logger.info(
                f"Context built successfully for disaster {disaster_data.disaster_id} "
                f"with {completeness:.2f} completeness"
            )

            return context

        except Exception as e:
            logger.error(
                f"Failed to build context for disaster {disaster_data.disaster_id}: {e}")
            raise

    def enrich_context(self, context: StructuredContext) -> EnrichedContext:
        """
        Enrich structured context with additional analysis and recommendations.

        Args:
            context: Base structured context

        Returns:
            EnrichedContext: Context with additional analysis

        Raises:
            ContextValidationError: If context is invalid for enrichment
        """
        self._validate_context(context)

        # Calculate priority factors for decision making
        priority_factors = self._calculate_priority_factors(context)

        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(context)

        # Create alternative scenarios
        alternative_scenarios = self._generate_alternative_scenarios(context)

        # Calculate confidence metrics
        confidence_metrics = self._calculate_confidence_metrics(context)

        return EnrichedContext(
            base_context=context,
            priority_factors=priority_factors,
            recommended_actions=recommended_actions,
            alternative_scenarios=alternative_scenarios,
            confidence_metrics=confidence_metrics
        )

    def _validate_context(self, context: StructuredContext) -> None:
        """
        Validate structured context before passing to prioritization.

        Args:
            context: Context to validate

        Raises:
            ContextValidationError: If validation fails
        """
        errors = []

        # Validate disaster info
        if not context.disaster_info:
            errors.append("Missing disaster information")
        elif not context.disaster_info.disaster_id:
            errors.append("Missing disaster ID")
        elif not context.disaster_info.affected_areas:
            errors.append("Missing affected areas")

        # Validate geographical context
        if not context.geographical_context:
            errors.append("Missing geographical context")
        elif not context.geographical_context.affected_areas:
            errors.append("Missing affected areas in geographical context")

        # Validate population data
        if not context.affected_population:
            errors.append("Missing population data")
        elif context.affected_population.total_population < 0:
            errors.append("Invalid total population (negative)")
        elif context.affected_population.vulnerable_population < 0:
            errors.append("Invalid vulnerable population (negative)")

        # Validate resource inventory
        if not context.available_resources:
            errors.append("Missing resource inventory")
        elif any(getattr(context.available_resources, attr) < 0
                 for attr in ['available_shelters', 'shelter_capacity', 'medical_facilities']):
            errors.append("Invalid resource counts (negative values)")

        # Validate risk assessment
        if not context.risk_assessment:
            errors.append("Missing risk assessment")
        else:
            risk = context.risk_assessment
            if not (0.0 <= risk.overall_risk_score <= 1.0):
                errors.append("Invalid overall risk score (must be 0.0-1.0)")
            if not (0.0 <= risk.evacuation_difficulty <= 1.0):
                errors.append(
                    "Invalid evacuation difficulty (must be 0.0-1.0)")
            if not (0.0 <= risk.time_criticality <= 1.0):
                errors.append("Invalid time criticality (must be 0.0-1.0)")
            if not (0.0 <= risk.resource_availability <= 1.0):
                errors.append(
                    "Invalid resource availability (must be 0.0-1.0)")

        # Validate context completeness
        if not (0.0 <= context.context_completeness <= 1.0):
            errors.append("Invalid context completeness (must be 0.0-1.0)")

        # Check for critical missing data that would prevent prioritization
        critical_missing = [
            indicator for indicator in context.missing_data_indicators
            if indicator in ['safe_locations', 'evacuation_routes']
        ]

        if critical_missing and context.context_completeness < 0.3:
            errors.append(
                f"Context too incomplete for prioritization: missing {critical_missing}")

        if errors:
            error_msg = f"Context validation failed: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ContextValidationError(error_msg)

        logger.debug("Context validation passed")

    def _handle_partial_context(self, context: StructuredContext) -> StructuredContext:
        """
        Handle partial context scenarios with missing information indicators.

        Args:
            context: Context that may be incomplete

        Returns:
            StructuredContext: Context with appropriate handling for missing data
        """
        # If context is too incomplete, add default values where safe
        if context.context_completeness < 0.5:
            logger.warning(
                f"Handling partial context with completeness {context.context_completeness:.2f}"
            )

            # Add default safe locations if none found
            if not context.geographical_context.safe_locations:
                # Create a default safe location based on disaster location
                disaster_location = context.disaster_info.location
                default_safe_location = Location(
                    latitude=disaster_location.latitude + 0.01,  # Slightly offset
                    longitude=disaster_location.longitude + 0.01,
                    address="Emergency Assembly Point",
                    administrative_area="emergency_default"
                )
                context.geographical_context.safe_locations = [
                    default_safe_location]

                if "safe_locations" not in context.missing_data_indicators:
                    context.missing_data_indicators.append(
                        "safe_locations_defaulted")

            # Add default evacuation route if none found
            if not context.evacuation_routes and context.geographical_context.safe_locations:
                default_route = EvacuationRoute(
                    route_id=f"{context.disaster_info.disaster_id}_default",
                    start_location=context.disaster_info.location,
                    end_location=context.geographical_context.safe_locations[0],
                    distance_km=context.disaster_info.location.distance_to(
                        context.geographical_context.safe_locations[0]
                    ),
                    estimated_time_minutes=30,  # Default estimate
                    capacity=100,  # Default capacity
                    current_load=0,
                    route_geometry=[
                        context.disaster_info.location,
                        context.geographical_context.safe_locations[0]
                    ],
                    safe_location_name="Emergency Assembly Point",
                    safe_location_category="emergency_default"
                )
                context.evacuation_routes = [default_route]

                if "evacuation_routes" not in context.missing_data_indicators:
                    context.missing_data_indicators.append(
                        "evacuation_routes_defaulted")

        return context

    def _calculate_priority_factors(self, context: StructuredContext) -> Dict[str, float]:
        """Calculate priority factors for decision making."""
        return {
            "population_impact": min(1.0, context.affected_population.total_population / 10000),
            "severity_factor": context.risk_assessment.overall_risk_score,
            "time_sensitivity": context.risk_assessment.time_criticality,
            "resource_constraint": 1.0 - context.risk_assessment.resource_availability,
            "evacuation_complexity": context.risk_assessment.evacuation_difficulty
        }

    def _generate_recommended_actions(self, context: StructuredContext) -> List[str]:
        """Generate recommended actions based on context."""
        actions = []

        # High-risk situations
        if context.risk_assessment.overall_risk_score > 0.7:
            actions.append("Immediate evacuation alert")
            actions.append("Deploy emergency response teams")

        # Resource constraints
        if context.risk_assessment.resource_availability < 0.3:
            actions.append("Request additional resources")
            actions.append("Coordinate with neighboring jurisdictions")

        # High population impact
        if context.affected_population.total_population > 5000:
            actions.append("Activate mass notification systems")
            actions.append("Establish evacuation coordination centers")

        # Evacuation difficulties
        if context.risk_assessment.evacuation_difficulty > 0.6:
            actions.append("Deploy traffic management teams")
            actions.append("Activate alternative evacuation routes")

        return actions

    def _generate_alternative_scenarios(self, context: StructuredContext) -> List[Dict[str, Any]]:
        """Generate alternative scenarios for contingency planning."""
        scenarios = []

        # Scenario 1: Escalation
        scenarios.append({
            "name": "Escalation Scenario",
            "description": "Disaster severity increases",
            "probability": 0.3,
            "impact_multiplier": 1.5,
            "required_actions": ["Expand evacuation zone", "Increase alert level"]
        })

        # Scenario 2: Resource shortage
        scenarios.append({
            "name": "Resource Shortage",
            "description": "Limited evacuation capacity",
            "probability": 0.2,
            "impact_multiplier": 1.2,
            "required_actions": ["Prioritize vulnerable populations", "Request mutual aid"]
        })

        return scenarios

    def _calculate_confidence_metrics(self, context: StructuredContext) -> Dict[str, float]:
        """Calculate confidence metrics for the context."""
        return {
            "data_completeness": context.context_completeness,
            "route_reliability": 0.8 if context.evacuation_routes else 0.3,
            "population_estimate_confidence": 0.7,  # Based on data sources
            "risk_assessment_confidence": 0.8,
            "overall_confidence": context.context_completeness * 0.8
        }

    async def _build_geographical_context(self, disaster_data: DisasterData) -> GeographicalContext:
        """Build geographical context including affected areas and safe locations."""
        try:
            # Extract affected areas from disaster data
            affected_areas = [
                area.center for area in disaster_data.affected_areas]

            # Get safe locations around the disaster area
            safe_locations = []
            for area in disaster_data.affected_areas:
                locations = await get_safe_locations(
                    area.center.latitude,
                    area.center.longitude,
                    max(area.radius_km, self.search_radius_km)
                )

                # Convert to Location objects
                for loc in locations:
                    safe_locations.append(Location(
                        latitude=loc["lat"],
                        longitude=loc["lon"],
                        address=loc["name"],
                        administrative_area=loc["category"]
                    ))

            # Remove duplicates based on coordinates
            unique_safe_locations = []
            seen_coords = set()
            for loc in safe_locations:
                coord_key = (round(loc.latitude, 6), round(loc.longitude, 6))
                if coord_key not in seen_coords:
                    unique_safe_locations.append(loc)
                    seen_coords.add(coord_key)

            return GeographicalContext(
                affected_areas=affected_areas,
                safe_locations=unique_safe_locations,
                blocked_routes=[],  # Would be populated from real-time traffic data
                accessible_routes=[],  # Would be populated from routing analysis
                terrain_difficulty=self._assess_terrain_difficulty(
                    disaster_data),
                weather_conditions=self._get_weather_conditions(disaster_data)
            )

        except Exception as e:
            logger.warning(f"Partial geographical context due to error: {e}")
            # Return minimal context with available data
            return GeographicalContext(
                affected_areas=[
                    area.center for area in disaster_data.affected_areas],
                safe_locations=[],
                blocked_routes=[],
                accessible_routes=[]
            )

    async def _get_evacuation_routes(self, disaster_data: DisasterData) -> List[EvacuationRoute]:
        """Get evacuation routes using the existing evacuation system."""
        routes = []

        try:
            for area in disaster_data.affected_areas:
                # Use existing evacuation route finding system
                route_data = await find_evacuation_routes(
                    user_lat=area.center.latitude,
                    user_lon=area.center.longitude,
                    radius_km=self.search_radius_km,
                    max_per_category=self.max_routes_per_category
                )

                # Convert to EvacuationRoute objects
                for category, category_routes in route_data["results"]["routes"].items():
                    for route_info in category_routes:
                        # Convert geometry coordinates to Location objects
                        geometry = []
                        for coord in route_info["route"]["geometry"]:
                            geometry.append(Location(
                                latitude=coord[1],  # OSRM returns [lon, lat]
                                longitude=coord[0]
                            ))

                        route = EvacuationRoute(
                            route_id=f"{disaster_data.disaster_id}_{category}_{len(routes)}",
                            start_location=area.center,
                            end_location=Location(
                                latitude=route_info["lat"],
                                longitude=route_info["lon"]
                            ),
                            distance_km=route_info["distance_km"],
                            estimated_time_minutes=int(
                                route_info["route"]["duration_s"] / 60),
                            capacity=self._estimate_route_capacity(
                                category, disaster_data.severity),
                            current_load=0,  # Would be populated from real-time data
                            route_geometry=geometry,
                            safe_location_name=route_info["safe_location"],
                            safe_location_category=category
                        )
                        routes.append(route)

        except Exception as e:
            logger.warning(f"Failed to get evacuation routes: {e}")
            # Continue with empty routes list

        return routes

    def _assess_population_impact(self, disaster_data: DisasterData) -> PopulationData:
        """Assess population impact based on disaster data and affected areas."""
        total_population = disaster_data.estimated_impact.estimated_affected_population

        # Estimate vulnerable population (typically 15-25% of total)
        vulnerable_ratio = 0.2
        if disaster_data.disaster_type in [DisasterType.EARTHQUAKE, DisasterType.BUILDING_COLLAPSE]:
            vulnerable_ratio = 0.25  # Higher vulnerability for structural disasters
        elif disaster_data.disaster_type in [DisasterType.CHEMICAL_SPILL, DisasterType.EXPLOSION]:
            vulnerable_ratio = 0.3  # Higher vulnerability for toxic/explosive disasters

        vulnerable_population = int(total_population * vulnerable_ratio)

        # Estimate current occupancy based on time of day and disaster type
        current_occupancy = self._estimate_current_occupancy(
            disaster_data, total_population)

        # Calculate population density
        total_area = sum(
            3.14159 * (area.radius_km ** 2) for area in disaster_data.affected_areas
        )
        population_density = total_population / total_area if total_area > 0 else 0

        return PopulationData(
            total_population=total_population,
            vulnerable_population=vulnerable_population,
            current_occupancy=current_occupancy,
            population_density_per_km2=population_density
        )

    def _inventory_resources(
        self, disaster_data: DisasterData, geo_context: GeographicalContext
    ) -> ResourceInventory:
        """Inventory available resources for disaster response."""
        # Count safe locations by category
        shelters = sum(1 for loc in geo_context.safe_locations
                       if loc.administrative_area in ["bunkers_shelters", "underground_parking"])
        medical_facilities = sum(1 for loc in geo_context.safe_locations
                                 if loc.administrative_area == "hospitals")

        # Estimate capacities based on disaster severity and type
        base_shelter_capacity = 100
        if disaster_data.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            base_shelter_capacity = 150

        return ResourceInventory(
            available_shelters=shelters,
            shelter_capacity=shelters * base_shelter_capacity,
            medical_facilities=medical_facilities,
            # Estimate based on shelters
            emergency_vehicles=max(1, shelters // 2),
            communication_systems=1,  # Assume basic communication available
            # Based on medical facilities
            backup_power_systems=max(1, medical_facilities)
        )

    def _calculate_risk_metrics(
        self,
        disaster_data: DisasterData,
        geo_context: GeographicalContext,
        routes: List[EvacuationRoute],
        population: PopulationData
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for the disaster."""
        # Base risk score from disaster type and severity
        type_risk_map = {
            DisasterType.FIRE: 0.7,
            DisasterType.EXPLOSION: 0.9,
            DisasterType.CHEMICAL_SPILL: 0.8,
            DisasterType.EARTHQUAKE: 0.8,
            DisasterType.BUILDING_COLLAPSE: 0.9,
            DisasterType.FLOOD: 0.6,
            DisasterType.TORNADO: 0.8,
            DisasterType.VOLCANIC: 0.7,
            DisasterType.ELECTRICAL: 0.5,
            DisasterType.TERRORIST_ATTACK: 0.9
        }

        severity_multiplier = {
            SeverityLevel.LOW: 0.3,
            SeverityLevel.MEDIUM: 0.6,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.CRITICAL: 1.0
        }

        base_risk = type_risk_map.get(disaster_data.disaster_type, 0.5)
        severity_factor = severity_multiplier.get(disaster_data.severity, 0.5)
        overall_risk = min(1.0, base_risk * severity_factor)

        # Evacuation difficulty based on available routes and population
        evacuation_difficulty = 0.5  # Default
        if routes:
            total_capacity = sum(route.capacity for route in routes)
            if population.current_occupancy and total_capacity > 0:
                capacity_ratio = population.current_occupancy / total_capacity
                evacuation_difficulty = min(1.0, capacity_ratio)
        else:
            evacuation_difficulty = 0.9  # High difficulty if no routes

        # Time criticality based on disaster type
        time_critical_disasters = [
            DisasterType.EXPLOSION, DisasterType.CHEMICAL_SPILL,
            DisasterType.BUILDING_COLLAPSE, DisasterType.FIRE
        ]
        time_criticality = 0.9 if disaster_data.disaster_type in time_critical_disasters else 0.5

        # Resource availability
        safe_location_count = len(geo_context.safe_locations)
        resource_availability = min(
            1.0, safe_location_count / max(1, population.total_population / 1000))

        return RiskMetrics(
            overall_risk_score=overall_risk,
            evacuation_difficulty=evacuation_difficulty,
            time_criticality=time_criticality,
            resource_availability=resource_availability,
            weather_impact=self._assess_weather_impact(disaster_data),
            traffic_congestion=0.5  # Would be populated from real-time traffic data
        )

    def _assess_completeness(
        self,
        geo_context: GeographicalContext,
        routes: List[EvacuationRoute],
        population: PopulationData,
        resources: ResourceInventory
    ) -> tuple[float, List[str]]:
        """Assess context completeness and identify missing data."""
        completeness_factors = []
        missing_indicators = []

        # Geographical context completeness
        if geo_context.safe_locations:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.0)
            missing_indicators.append("safe_locations")

        # Evacuation routes completeness
        if routes:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.0)
            missing_indicators.append("evacuation_routes")

        # Population data completeness
        if population.current_occupancy is not None:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.7)
            missing_indicators.append("current_occupancy")

        # Resource inventory completeness
        if resources.available_shelters > 0:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.3)
            missing_indicators.append("shelter_resources")

        # Weather and traffic data
        if geo_context.weather_conditions:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.8)
            missing_indicators.append("weather_conditions")

        overall_completeness = sum(
            completeness_factors) / len(completeness_factors)

        return overall_completeness, missing_indicators

    def _assess_terrain_difficulty(self, disaster_data: DisasterData) -> Optional[float]:
        """Assess terrain difficulty for evacuation."""
        # Simplified terrain assessment based on disaster type
        difficult_terrain_disasters = [
            DisasterType.EARTHQUAKE, DisasterType.VOLCANIC, DisasterType.FLOOD
        ]

        if disaster_data.disaster_type in difficult_terrain_disasters:
            return 0.7
        return 0.3

    def _get_weather_conditions(self, disaster_data: DisasterData) -> Optional[Dict[str, Any]]:
        """Get weather conditions (placeholder for real weather API integration)."""
        # This would integrate with a weather API in a real implementation
        return {
            "temperature": 20.0,
            "conditions": "clear",
            "wind_speed": 5.0,
            "visibility": "good"
        }

    def _estimate_route_capacity(self, category: str, severity: SeverityLevel) -> int:
        """Estimate evacuation route capacity based on category and severity."""
        base_capacities = {
            "hospitals": 200,
            "bunkers_shelters": 500,
            "underground_parking": 100
        }

        base_capacity = base_capacities.get(category, 100)

        # Reduce capacity for higher severity disasters due to congestion
        severity_factors = {
            SeverityLevel.LOW: 1.0,
            SeverityLevel.MEDIUM: 0.8,
            SeverityLevel.HIGH: 0.6,
            SeverityLevel.CRITICAL: 0.4
        }

        return int(base_capacity * severity_factors.get(severity, 0.5))

    def _estimate_current_occupancy(self, disaster_data: DisasterData, total_population: int) -> Optional[int]:
        """Estimate current occupancy based on time and disaster type."""
        hour = disaster_data.timestamp.hour

        # Time-based occupancy factors
        if 9 <= hour <= 17:  # Business hours
            occupancy_factor = 0.7  # Many people at work/school
        elif 22 <= hour or hour <= 6:  # Night hours
            occupancy_factor = 0.9  # Most people at home
        else:  # Evening/morning
            occupancy_factor = 0.8

        # Disaster type adjustments
        if disaster_data.disaster_type in [DisasterType.EARTHQUAKE, DisasterType.EXPLOSION]:
            occupancy_factor += 0.1  # People tend to stay put initially

        return int(total_population * min(1.0, occupancy_factor))

    def _assess_weather_impact(self, disaster_data: DisasterData) -> Optional[float]:
        """Assess weather impact on evacuation (placeholder)."""
        # This would integrate with real weather data
        weather_sensitive_disasters = [
            DisasterType.FIRE, DisasterType.FLOOD, DisasterType.TORNADO
        ]

        if disaster_data.disaster_type in weather_sensitive_disasters:
            return 0.6  # Moderate weather impact
        return 0.2  # Low weather impact
