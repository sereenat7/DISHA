"""
Alert Prioritizer component for analyzing disaster context and determining alert priorities.
"""

import logging
from typing import List, Dict, Any, Tuple
from datetime import timedelta
from dataclasses import dataclass

from .models.alert_priority import AlertPriority, PriorityLevel, ResourceType
from .models.context import StructuredContext, RiskMetrics
from .models.disaster_data import DisasterType, SeverityLevel
from .core.exceptions import PriorityAnalysisError

logger = logging.getLogger(__name__)


@dataclass
class RankedDisaster:
    """Represents a disaster with its priority ranking."""
    disaster_id: str
    context: StructuredContext
    priority: AlertPriority
    rank: int  # 1 = highest priority
    comparative_urgency: float  # 0.0 - 1.0 relative to other disasters


class AlertPrioritizer:
    """
    Analyzes disaster context to determine appropriate alert priorities using
    weighted scoring algorithms based on emergency management best practices.
    """

    # Priority scoring weights (must sum to 1.0)
    POPULATION_WEIGHT = 0.40  # Affected population size
    GEOGRAPHICAL_WEIGHT = 0.25  # Geographical scope and accessibility
    EVACUATION_WEIGHT = 0.20  # Available evacuation routes and capacity
    TIME_SENSITIVITY_WEIGHT = 0.15  # Time sensitivity and disaster type

    # Priority thresholds for score ranges
    CRITICAL_THRESHOLD = 0.85
    HIGH_THRESHOLD = 0.65
    MEDIUM_THRESHOLD = 0.35

    # Disaster type severity multipliers
    DISASTER_TYPE_MULTIPLIERS = {
        DisasterType.EXPLOSION: 1.0,
        DisasterType.TERRORIST_ATTACK: 1.0,
        DisasterType.BUILDING_COLLAPSE: 0.95,
        DisasterType.FIRE: 0.90,
        DisasterType.CHEMICAL_SPILL: 0.85,
        DisasterType.EARTHQUAKE: 0.80,
        DisasterType.FLOOD: 0.75,
        DisasterType.TORNADO: 0.70,
        DisasterType.ELECTRICAL: 0.60,
        DisasterType.VOLCANIC: 0.55,
    }

    def __init__(self):
        """Initialize the AlertPrioritizer."""
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validate that priority weights sum to 1.0."""
        total_weight = (
            self.POPULATION_WEIGHT +
            self.GEOGRAPHICAL_WEIGHT +
            self.EVACUATION_WEIGHT +
            self.TIME_SENSITIVITY_WEIGHT
        )
        if abs(total_weight - 1.0) > 0.001:  # Allow small floating point errors
            raise ValueError(
                f"Priority weights must sum to 1.0, got {total_weight}")

    def analyze_priority(self, context: StructuredContext) -> AlertPriority:
        """
        Analyze disaster context and determine appropriate alert priority.

        Args:
            context: Structured context containing disaster and situational data

        Returns:
            AlertPriority with level, score, and supporting information

        Raises:
            PriorityAnalysisError: If priority analysis fails
        """
        try:
            logger.info(
                f"Analyzing priority for disaster {context.disaster_info.disaster_id}")

            # Calculate component scores
            population_score = self._calculate_population_score(context)
            geographical_score = self._calculate_geographical_score(context)
            evacuation_score = self._calculate_evacuation_score(context)
            time_sensitivity_score = self._calculate_time_sensitivity_score(
                context)

            # Calculate weighted total score
            total_score = (
                population_score * self.POPULATION_WEIGHT +
                geographical_score * self.GEOGRAPHICAL_WEIGHT +
                evacuation_score * self.EVACUATION_WEIGHT +
                time_sensitivity_score * self.TIME_SENSITIVITY_WEIGHT
            )

            # Apply disaster type multiplier
            disaster_multiplier = self.DISASTER_TYPE_MULTIPLIERS.get(
                context.disaster_info.disaster_type, 0.75
            )
            final_score = min(total_score * disaster_multiplier, 1.0)

            # Determine priority level
            priority_level = self._score_to_priority_level(final_score)

            # Generate reasoning
            reasoning = self._generate_reasoning(
                context, final_score, population_score, geographical_score,
                evacuation_score, time_sensitivity_score, disaster_multiplier
            )

            # Determine required resources and response time
            required_resources = self._determine_required_resources(
                context, priority_level)
            response_time = self._estimate_response_time(priority_level)

            # Calculate confidence based on context completeness
            confidence = self._calculate_confidence(context)

            alert_priority = AlertPriority(
                level=priority_level,
                score=final_score,
                reasoning=reasoning,
                estimated_response_time=response_time,
                required_resources=required_resources,
                confidence=confidence
            )

            logger.info(
                f"Priority analysis complete for disaster {context.disaster_info.disaster_id}: "
                f"{priority_level.value} (score: {final_score:.3f})"
            )

            return alert_priority

        except Exception as e:
            error_msg = f"Priority analysis failed for disaster {context.disaster_info.disaster_id}: {str(e)}"
            logger.error(error_msg)
            raise PriorityAnalysisError(error_msg) from e

    def _calculate_population_score(self, context: StructuredContext) -> float:
        """Calculate score based on affected population (0.0 - 1.0)."""
        population_data = context.affected_population

        # Base score from total population (logarithmic scale)
        total_pop = population_data.total_population
        if total_pop <= 0:
            return 0.0

        # Logarithmic scaling: 1-100 people = 0.1-0.4, 100-10000 = 0.4-0.8, 10000+ = 0.8-1.0
        import math
        base_score = min(math.log10(total_pop) / 5.0, 1.0)

        # Boost for vulnerable population
        vulnerable_ratio = population_data.vulnerable_population / total_pop
        vulnerability_boost = vulnerable_ratio * 0.3  # Up to 30% boost

        # Boost for high population density
        density_boost = 0.0
        if population_data.population_density_per_km2:
            # High density (>1000/km²) gets boost
            if population_data.population_density_per_km2 > 1000:
                density_boost = min(
                    population_data.population_density_per_km2 / 5000, 0.2)

        return min(base_score + vulnerability_boost + density_boost, 1.0)

    def _calculate_geographical_score(self, context: StructuredContext) -> float:
        """Calculate score based on geographical scope and accessibility (0.0 - 1.0)."""
        geo_context = context.geographical_context

        # Base score from number of affected areas
        num_areas = len(context.disaster_info.affected_areas)
        area_score = min(num_areas / 10.0, 0.5)  # Up to 0.5 for many areas

        # Score from terrain difficulty
        terrain_score = 0.0
        if geo_context.terrain_difficulty:
            terrain_score = geo_context.terrain_difficulty * 0.3

        # Score from blocked routes (accessibility issues)
        route_score = 0.0
        total_routes = len(geo_context.blocked_routes) + \
            len(geo_context.accessible_routes)
        if total_routes > 0:
            blocked_ratio = len(geo_context.blocked_routes) / total_routes
            route_score = blocked_ratio * 0.4  # Up to 0.4 for all routes blocked

        # Weather impact
        weather_score = 0.0
        if geo_context.weather_conditions:
            # Simple heuristic: bad weather increases score
            weather_severity = geo_context.weather_conditions.get(
                'severity', 0.0)
            weather_score = weather_severity * 0.2

        return min(area_score + terrain_score + route_score + weather_score, 1.0)

    def _calculate_evacuation_score(self, context: StructuredContext) -> float:
        """Calculate score based on evacuation routes and capacity (0.0 - 1.0)."""
        evacuation_routes = context.evacuation_routes

        if not evacuation_routes:
            return 1.0  # No routes = maximum urgency

        # Calculate total capacity vs affected population
        total_capacity = sum(route.capacity for route in evacuation_routes)
        total_load = sum(route.current_load for route in evacuation_routes)
        affected_population = context.affected_population.total_population

        # Capacity utilization score
        if total_capacity > 0:
            utilization = total_load / total_capacity
            capacity_score = utilization * 0.5  # Up to 0.5 for full utilization
        else:
            capacity_score = 1.0

        # Population vs capacity ratio
        if total_capacity > 0 and affected_population > 0:
            demand_ratio = affected_population / total_capacity
            demand_score = min(demand_ratio, 1.0) * \
                0.4  # Up to 0.4 for high demand
        else:
            demand_score = 0.5

        # Route efficiency (average time)
        if evacuation_routes:
            avg_time = sum(
                route.estimated_time_minutes for route in evacuation_routes) / len(evacuation_routes)
            # Up to 0.3 for 2+ hour routes
            time_score = min(avg_time / 120.0, 0.3)
        else:
            time_score = 0.3

        return min(capacity_score + demand_score + time_score, 1.0)

    def _calculate_time_sensitivity_score(self, context: StructuredContext) -> float:
        """Calculate score based on time sensitivity and disaster type (0.0 - 1.0)."""
        disaster_info = context.disaster_info
        risk_metrics = context.risk_assessment

        # Base score from disaster severity
        severity_scores = {
            SeverityLevel.LOW: 0.2,
            SeverityLevel.MEDIUM: 0.4,
            SeverityLevel.HIGH: 0.7,
            SeverityLevel.CRITICAL: 1.0
        }
        severity_score = severity_scores.get(disaster_info.severity, 0.5)

        # Time criticality from risk metrics
        time_criticality = risk_metrics.time_criticality

        # Combine severity and time criticality
        return min((severity_score + time_criticality) / 2.0, 1.0)

    def _score_to_priority_level(self, score: float) -> PriorityLevel:
        """Convert numerical score to priority level."""
        if score >= self.CRITICAL_THRESHOLD:
            return PriorityLevel.CRITICAL
        elif score >= self.HIGH_THRESHOLD:
            return PriorityLevel.HIGH
        elif score >= self.MEDIUM_THRESHOLD:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW

    def _generate_reasoning(
        self, context: StructuredContext, final_score: float,
        population_score: float, geographical_score: float,
        evacuation_score: float, time_sensitivity_score: float,
        disaster_multiplier: float
    ) -> str:
        """Generate human-readable reasoning for priority assignment."""
        disaster_info = context.disaster_info

        reasoning_parts = [
            f"Disaster: {disaster_info.disaster_type.value} at {disaster_info.location.address or 'unknown location'}",
            f"Affected population: {context.affected_population.total_population:,} people",
            f"Severity: {disaster_info.severity.value}",
            f"Score breakdown: Population({population_score:.2f}) + Geography({geographical_score:.2f}) + "
            f"Evacuation({evacuation_score:.2f}) + Time({time_sensitivity_score:.2f}) "
            f"× Disaster multiplier({disaster_multiplier:.2f}) = {final_score:.3f}"
        ]

        # Add key factors
        if evacuation_score > 0.7:
            reasoning_parts.append("High evacuation difficulty detected")
        if population_score > 0.8:
            reasoning_parts.append("Large population impact")
        if geographical_score > 0.7:
            reasoning_parts.append("Challenging geographical conditions")

        return "; ".join(reasoning_parts)

    def _determine_required_resources(
        self, context: StructuredContext, priority_level: PriorityLevel
    ) -> List[ResourceType]:
        """Determine required resources based on disaster type and priority."""
        disaster_type = context.disaster_info.disaster_type

        # Base resources for all disasters
        base_resources = [ResourceType.COMMUNICATION,
                          ResourceType.EMERGENCY_SHELTER]

        # Disaster-specific resources
        disaster_resources = {
            DisasterType.FIRE: [ResourceType.FIRE_RESCUE, ResourceType.MEDICAL],
            DisasterType.EXPLOSION: [ResourceType.FIRE_RESCUE, ResourceType.MEDICAL, ResourceType.SEARCH_RESCUE],
            DisasterType.BUILDING_COLLAPSE: [ResourceType.SEARCH_RESCUE, ResourceType.MEDICAL],
            DisasterType.CHEMICAL_SPILL: [ResourceType.MEDICAL, ResourceType.UTILITIES],
            DisasterType.FLOOD: [ResourceType.EVACUATION_TRANSPORT, ResourceType.SEARCH_RESCUE],
            DisasterType.EARTHQUAKE: [ResourceType.SEARCH_RESCUE, ResourceType.MEDICAL, ResourceType.UTILITIES],
            DisasterType.TERRORIST_ATTACK: [ResourceType.POLICE, ResourceType.MEDICAL, ResourceType.SEARCH_RESCUE],
        }

        resources = base_resources + disaster_resources.get(disaster_type, [])

        # Add additional resources for high priority
        if priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
            resources.extend(
                [ResourceType.EVACUATION_TRANSPORT, ResourceType.UTILITIES])

        return list(set(resources))  # Remove duplicates

    def _estimate_response_time(self, priority_level: PriorityLevel) -> timedelta:
        """Estimate required response time based on priority level."""
        response_times = {
            PriorityLevel.CRITICAL: timedelta(minutes=5),
            PriorityLevel.HIGH: timedelta(minutes=15),
            PriorityLevel.MEDIUM: timedelta(hours=2),
            PriorityLevel.LOW: timedelta(hours=8)
        }
        return response_times[priority_level]

    def _calculate_confidence(self, context: StructuredContext) -> float:
        """Calculate confidence in priority assignment based on context completeness."""
        base_confidence = context.context_completeness

        # Reduce confidence if critical data is missing
        critical_missing = 0
        for indicator in context.missing_data_indicators:
            if any(critical in indicator.lower() for critical in ['population', 'evacuation', 'severity']):
                critical_missing += 1

        confidence_reduction = min(critical_missing * 0.15, 0.5)
        return max(base_confidence - confidence_reduction, 0.1)

    def rank_concurrent_disasters(self, contexts: List[StructuredContext]) -> List[RankedDisaster]:
        """
        Rank multiple concurrent disasters by comparative urgency.

        Args:
            contexts: List of structured contexts for concurrent disasters

        Returns:
            List of RankedDisaster objects sorted by priority (highest first)

        Raises:
            PriorityAnalysisError: If ranking fails
        """
        if not contexts:
            return []

        try:
            logger.info(f"Ranking {len(contexts)} concurrent disasters")

            # Analyze priority for each disaster
            disaster_priorities = []
            for context in contexts:
                try:
                    priority = self.analyze_priority(context)
                    disaster_priorities.append((context, priority))
                except Exception as e:
                    logger.warning(
                        f"Priority analysis failed for disaster {context.disaster_info.disaster_id}, "
                        f"using fallback: {str(e)}"
                    )
                    # Use fallback priority
                    fallback_priority = self._create_fallback_priority(
                        f"Priority analysis failed: {str(e)}"
                    )
                    disaster_priorities.append((context, fallback_priority))

            # Sort by priority score (highest first)
            disaster_priorities.sort(key=lambda x: x[1].score, reverse=True)

            # Calculate comparative urgency and create ranked disasters
            ranked_disasters = []
            max_score = disaster_priorities[0][1].score if disaster_priorities else 1.0

            for rank, (context, priority) in enumerate(disaster_priorities, 1):
                # Calculate comparative urgency relative to highest priority disaster
                comparative_urgency = priority.score / max_score if max_score > 0 else 0.5

                ranked_disaster = RankedDisaster(
                    disaster_id=context.disaster_info.disaster_id,
                    context=context,
                    priority=priority,
                    rank=rank,
                    comparative_urgency=comparative_urgency
                )
                ranked_disasters.append(ranked_disaster)

            # Log ranking results
            self._log_ranking_results(ranked_disasters)

            return ranked_disasters

        except Exception as e:
            error_msg = f"Failed to rank concurrent disasters: {str(e)}"
            logger.error(error_msg)
            raise PriorityAnalysisError(error_msg) from e

    def _create_fallback_priority(self, reasoning: str) -> AlertPriority:
        """
        Create a fallback HIGH priority when priority determination fails.

        Args:
            reasoning: Explanation of why fallback was used

        Returns:
            AlertPriority with HIGH level and default values
        """
        logger.warning(f"Using fallback priority: {reasoning}")

        return AlertPriority.create_default_high_priority(
            reasoning=f"FALLBACK: {reasoning}"
        )

    def analyze_priority_with_fallback(self, context: StructuredContext) -> AlertPriority:
        """
        Analyze priority with automatic fallback to HIGH priority on failure.

        Args:
            context: Structured context containing disaster and situational data

        Returns:
            AlertPriority (either analyzed or fallback HIGH priority)
        """
        try:
            return self.analyze_priority(context)
        except Exception as e:
            logger.error(
                f"Priority analysis failed for disaster {context.disaster_info.disaster_id}, "
                f"using fallback HIGH priority: {str(e)}"
            )
            return self._create_fallback_priority(
                f"Analysis failed for {context.disaster_info.disaster_id}: {str(e)}"
            )

    def _log_ranking_results(self, ranked_disasters: List[RankedDisaster]) -> None:
        """Log the results of disaster ranking for monitoring."""
        logger.info("Disaster ranking results:")
        for disaster in ranked_disasters:
            logger.info(
                f"  Rank {disaster.rank}: {disaster.disaster_id} "
                f"({disaster.priority.level.value}, score: {disaster.priority.score:.3f}, "
                f"urgency: {disaster.comparative_urgency:.3f})"
            )

        # Log any fallback priorities used
        fallback_count = sum(
            1 for d in ranked_disasters
            if "FALLBACK" in d.priority.reasoning
        )
        if fallback_count > 0:
            logger.warning(
                f"{fallback_count} disasters used fallback priority due to analysis failures")

    def get_priority_statistics(self, ranked_disasters: List[RankedDisaster]) -> Dict[str, Any]:
        """
        Get statistical information about disaster priorities.

        Args:
            ranked_disasters: List of ranked disasters

        Returns:
            Dictionary containing priority statistics
        """
        if not ranked_disasters:
            return {}

        # Count by priority level
        level_counts = {}
        for level in PriorityLevel:
            level_counts[level.value] = sum(
                1 for d in ranked_disasters if d.priority.level == level
            )

        # Calculate score statistics
        scores = [d.priority.score for d in ranked_disasters]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        # Count fallbacks
        fallback_count = sum(
            1 for d in ranked_disasters
            if "FALLBACK" in d.priority.reasoning
        )

        # Calculate confidence statistics
        confidences = [
            d.priority.confidence for d in ranked_disasters if d.priority.confidence is not None]
        avg_confidence = sum(confidences) / \
            len(confidences) if confidences else None

        return {
            "total_disasters": len(ranked_disasters),
            "priority_distribution": level_counts,
            "score_statistics": {
                "average": avg_score,
                "maximum": max_score,
                "minimum": min_score
            },
            "fallback_count": fallback_count,
            "fallback_percentage": (fallback_count / len(ranked_disasters)) * 100,
            "average_confidence": avg_confidence,
            "highest_priority_disaster": ranked_disasters[0].disaster_id,
            "lowest_priority_disaster": ranked_disasters[-1].disaster_id
        }
