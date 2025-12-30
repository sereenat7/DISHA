"""
Property-based tests for Alert Prioritizer component.

Feature: agentic-disaster-response, Property 6: Priority Analysis Consistency
Feature: agentic-disaster-response, Property 7: Multi-Disaster Ranking
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume
from unittest.mock import patch, MagicMock

from agentic_disaster_response.alert_prioritizer import AlertPrioritizer, RankedDisaster
from agentic_disaster_response.models import (
    DisasterData, DisasterType, SeverityLevel, Location,
    ImpactAssessment, GeographicalArea, AlertPriority, PriorityLevel,
    StructuredContext, GeographicalContext, EvacuationRoute,
    PopulationData, ResourceInventory, RiskMetrics
)
from agentic_disaster_response.core.exceptions import PriorityAnalysisError


# Hypothesis strategies for generating test data
@st.composite
def location_strategy(draw):
    """Generate valid Location objects."""
    lat = draw(st.floats(min_value=-90, max_value=90))
    lon = draw(st.floats(min_value=-180, max_value=180))
    address = draw(st.one_of(st.none(), st.text(min_size=1, max_size=100)))
    admin_area = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    country = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))

    return Location(
        latitude=lat,
        longitude=lon,
        address=address,
        administrative_area=admin_area,
        country=country
    )


@st.composite
def disaster_data_strategy(draw):
    """Generate valid DisasterData objects."""
    disaster_id = draw(st.text(min_size=1, max_size=50))
    disaster_type = draw(st.sampled_from(DisasterType))
    location = draw(location_strategy())
    severity = draw(st.sampled_from(SeverityLevel))
    timestamp = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    ))

    # Generate affected areas
    affected_areas = draw(st.lists(
        st.builds(
            GeographicalArea,
            center=location_strategy(),
            radius_km=st.floats(min_value=0.1, max_value=100.0),
            area_name=st.one_of(st.none(), st.text(min_size=1, max_size=50))
        ),
        min_size=1,
        max_size=5
    ))

    # Generate impact assessment
    estimated_impact = draw(st.builds(
        ImpactAssessment,
        estimated_affected_population=st.integers(
            min_value=1, max_value=1000000),
        estimated_casualties=st.one_of(
            st.none(), st.integers(min_value=0, max_value=10000)),
        infrastructure_damage_level=st.sampled_from(SeverityLevel),
        economic_impact_estimate=st.one_of(
            st.none(), st.floats(min_value=0, max_value=1e12)),
        environmental_impact=st.one_of(
            st.none(), st.text(min_size=1, max_size=200))
    ))

    return DisasterData(
        disaster_id=disaster_id,
        disaster_type=disaster_type,
        location=location,
        severity=severity,
        timestamp=timestamp,
        affected_areas=affected_areas,
        estimated_impact=estimated_impact,
        description=draw(
            st.one_of(st.none(), st.text(min_size=1, max_size=500))),
        source=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    )


@st.composite
def evacuation_route_strategy(draw):
    """Generate valid EvacuationRoute objects."""
    route_id = draw(st.text(min_size=1, max_size=50))
    start_location = draw(location_strategy())
    end_location = draw(location_strategy())
    distance_km = draw(st.floats(min_value=0.1, max_value=100.0))
    estimated_time_minutes = draw(st.integers(min_value=1, max_value=300))
    capacity = draw(st.integers(min_value=1, max_value=10000))
    current_load = draw(st.integers(min_value=0, max_value=capacity))

    route_geometry = draw(st.lists(
        location_strategy(),
        min_size=2,
        max_size=10
    ))

    safe_location_name = draw(st.text(min_size=1, max_size=100))
    safe_location_category = draw(st.sampled_from(
        ["hospitals", "bunkers_shelters", "underground_parking"]))

    return EvacuationRoute(
        route_id=route_id,
        start_location=start_location,
        end_location=end_location,
        distance_km=distance_km,
        estimated_time_minutes=estimated_time_minutes,
        capacity=capacity,
        current_load=current_load,
        route_geometry=route_geometry,
        safe_location_name=safe_location_name,
        safe_location_category=safe_location_category
    )


@st.composite
def structured_context_strategy(draw):
    """Generate valid StructuredContext objects."""
    disaster_info = draw(disaster_data_strategy())

    # Generate geographical context
    affected_areas = [area.center for area in disaster_info.affected_areas]
    safe_locations = draw(
        st.lists(location_strategy(), min_size=1, max_size=10))
    blocked_routes = draw(
        st.lists(st.text(min_size=1, max_size=20), max_size=5))
    accessible_routes = draw(
        st.lists(st.text(min_size=1, max_size=20), max_size=10))
    terrain_difficulty = draw(
        st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)))

    geographical_context = GeographicalContext(
        affected_areas=affected_areas,
        safe_locations=safe_locations,
        blocked_routes=blocked_routes,
        accessible_routes=accessible_routes,
        terrain_difficulty=terrain_difficulty,
        weather_conditions=draw(st.one_of(st.none(), st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.floats(min_value=0.0, max_value=1.0),
            max_size=3
        )))
    )

    # Generate evacuation routes
    evacuation_routes = draw(
        st.lists(evacuation_route_strategy(), min_size=0, max_size=5))

    # Generate population data
    total_population = disaster_info.estimated_impact.estimated_affected_population
    vulnerable_population = draw(st.integers(
        min_value=0, max_value=total_population))

    affected_population = PopulationData(
        total_population=total_population,
        vulnerable_population=vulnerable_population,
        current_occupancy=draw(st.one_of(st.none(), st.integers(
            min_value=0, max_value=total_population))),
        population_density_per_km2=draw(
            st.one_of(st.none(), st.floats(min_value=1.0, max_value=10000.0)))
    )

    # Generate resource inventory
    available_resources = ResourceInventory(
        available_shelters=draw(st.integers(min_value=0, max_value=100)),
        shelter_capacity=draw(st.integers(min_value=0, max_value=50000)),
        medical_facilities=draw(st.integers(min_value=0, max_value=50)),
        emergency_vehicles=draw(st.integers(min_value=0, max_value=200)),
        communication_systems=draw(st.integers(min_value=0, max_value=100)),
        backup_power_systems=draw(st.integers(min_value=0, max_value=50))
    )

    # Generate risk metrics
    risk_assessment = RiskMetrics(
        overall_risk_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        evacuation_difficulty=draw(st.floats(min_value=0.0, max_value=1.0)),
        time_criticality=draw(st.floats(min_value=0.0, max_value=1.0)),
        resource_availability=draw(st.floats(min_value=0.0, max_value=1.0)),
        weather_impact=draw(
            st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0))),
        traffic_congestion=draw(
            st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)))
    )

    context_completeness = draw(st.floats(min_value=0.0, max_value=1.0))
    missing_data_indicators = draw(
        st.lists(st.text(min_size=1, max_size=50), max_size=5))

    return StructuredContext(
        disaster_info=disaster_info,
        geographical_context=geographical_context,
        evacuation_routes=evacuation_routes,
        affected_population=affected_population,
        available_resources=available_resources,
        risk_assessment=risk_assessment,
        context_completeness=context_completeness,
        missing_data_indicators=missing_data_indicators
    )


class TestPriorityAnalysisConsistency:
    """
    Property 6: Priority Analysis Consistency

    For any structured context, the Alert Prioritizer should analyze severity indicators 
    considering affected population, geographical scope, and evacuation routes, then assign 
    a valid priority level (Critical, High, Medium, Low).

    **Validates: Requirements 3.1, 3.2, 3.3**
    """

    @given(context=structured_context_strategy())
    @pytest.mark.property
    def test_priority_analysis_consistency(self, context):
        """
        Property test: For any structured context, priority analysis should 
        consistently produce valid results with proper scoring and reasoning.
        """
        prioritizer = AlertPrioritizer()

        # Analyze priority
        priority = prioritizer.analyze_priority(context)

        # Validate that priority is properly structured
        assert isinstance(priority, AlertPriority)
        assert priority.level in PriorityLevel
        assert 0.0 <= priority.score <= 1.0
        assert isinstance(priority.reasoning, str)
        assert len(priority.reasoning) > 0
        assert isinstance(priority.estimated_response_time, timedelta)
        assert isinstance(priority.required_resources, list)
        assert priority.confidence is None or (
            0.0 <= priority.confidence <= 1.0)

        # Validate score-to-level consistency
        if priority.score >= prioritizer.CRITICAL_THRESHOLD:
            assert priority.level == PriorityLevel.CRITICAL
        elif priority.score >= prioritizer.HIGH_THRESHOLD:
            assert priority.level == PriorityLevel.HIGH
        elif priority.score >= prioritizer.MEDIUM_THRESHOLD:
            assert priority.level == PriorityLevel.MEDIUM
        else:
            assert priority.level == PriorityLevel.LOW

        # Validate response time consistency with priority level
        response_time_ranges = {
            PriorityLevel.CRITICAL: timedelta(minutes=10),
            PriorityLevel.HIGH: timedelta(minutes=30),
            PriorityLevel.MEDIUM: timedelta(hours=4),
            PriorityLevel.LOW: timedelta(hours=12)
        }
        assert priority.estimated_response_time <= response_time_ranges[priority.level]

        # Validate that reasoning contains key information
        assert context.disaster_info.disaster_type.value in priority.reasoning
        # Check for population in reasoning (could be formatted with commas)
        population_str = f"{context.affected_population.total_population:,}"
        assert population_str in priority.reasoning
        assert context.disaster_info.severity.value in priority.reasoning

    @given(context=structured_context_strategy())
    @pytest.mark.property
    def test_severity_indicators_consideration(self, context):
        """
        Property test: For any context, priority analysis should consider 
        affected population, geographical scope, and evacuation routes.
        """
        prioritizer = AlertPrioritizer()

        # Test with different population sizes
        original_population = context.affected_population.total_population

        # Create context with larger population
        large_pop_context = StructuredContext(
            disaster_info=context.disaster_info,
            geographical_context=context.geographical_context,
            evacuation_routes=context.evacuation_routes,
            affected_population=PopulationData(
                total_population=original_population * 10,  # 10x larger
                vulnerable_population=context.affected_population.vulnerable_population * 10,
                current_occupancy=context.affected_population.current_occupancy,
                population_density_per_km2=context.affected_population.population_density_per_km2
            ),
            available_resources=context.available_resources,
            risk_assessment=context.risk_assessment,
            context_completeness=context.context_completeness,
            missing_data_indicators=context.missing_data_indicators
        )

        original_priority = prioritizer.analyze_priority(context)
        large_pop_priority = prioritizer.analyze_priority(large_pop_context)

        # Larger population should generally result in higher or equal priority score
        # (unless other factors significantly reduce it)
        if original_population > 0:  # Avoid division by zero
            population_increase_factor = (
                original_population * 10) / original_population
            # Allow for some variance due to other factors, but expect general increase
            assert large_pop_priority.score >= original_priority.score * 0.8

    @given(context=structured_context_strategy())
    @pytest.mark.property
    def test_evacuation_route_impact_on_priority(self, context):
        """
        Property test: For any context, evacuation route availability and capacity 
        should impact priority scoring appropriately.
        """
        prioritizer = AlertPrioritizer()

        # Test with no evacuation routes (should increase urgency)
        no_routes_context = StructuredContext(
            disaster_info=context.disaster_info,
            geographical_context=context.geographical_context,
            evacuation_routes=[],  # No routes available
            affected_population=context.affected_population,
            available_resources=context.available_resources,
            risk_assessment=context.risk_assessment,
            context_completeness=context.context_completeness,
            missing_data_indicators=context.missing_data_indicators
        )

        original_priority = prioritizer.analyze_priority(context)
        no_routes_priority = prioritizer.analyze_priority(no_routes_context)

        # No evacuation routes should generally result in higher priority
        # (unless original context already had very poor evacuation situation)
        if context.evacuation_routes:  # Only compare if original had routes
            assert no_routes_priority.score >= original_priority.score


class TestMultiDisasterRanking:
    """
    Property 7: Multi-Disaster Ranking

    For any set of concurrent disasters, the Alert Prioritizer should rank them by 
    comparative urgency and handle priority determination failures by defaulting to 
    High priority with uncertainty logging.

    **Validates: Requirements 3.4, 3.5**
    """

    @given(contexts=st.lists(structured_context_strategy(), min_size=1, max_size=10))
    @pytest.mark.property
    def test_multi_disaster_ranking_consistency(self, contexts):
        """
        Property test: For any list of disaster contexts, ranking should 
        produce consistent, properly ordered results.
        """
        prioritizer = AlertPrioritizer()

        # Ensure unique disaster IDs
        for i, context in enumerate(contexts):
            context.disaster_info.disaster_id = f"disaster-{i}"

        # Rank disasters
        ranked_disasters = prioritizer.rank_concurrent_disasters(contexts)

        # Validate basic structure
        assert len(ranked_disasters) == len(contexts)
        assert all(isinstance(rd, RankedDisaster) for rd in ranked_disasters)

        # Validate ranking order (highest score first)
        for i in range(len(ranked_disasters) - 1):
            current = ranked_disasters[i]
            next_disaster = ranked_disasters[i + 1]

            # Scores should be in descending order
            assert current.priority.score >= next_disaster.priority.score

            # Ranks should be sequential
            assert current.rank == i + 1
            assert next_disaster.rank == i + 2

        # Validate comparative urgency calculation
        if ranked_disasters:
            max_score = ranked_disasters[0].priority.score
            for disaster in ranked_disasters:
                if max_score > 0:
                    expected_urgency = disaster.priority.score / max_score
                    assert abs(disaster.comparative_urgency -
                               expected_urgency) < 0.001
                else:
                    assert disaster.comparative_urgency == 0.5  # Default when max_score is 0

        # Validate that all disaster IDs are preserved
        ranked_ids = {rd.disaster_id for rd in ranked_disasters}
        original_ids = {ctx.disaster_info.disaster_id for ctx in contexts}
        assert ranked_ids == original_ids

    @given(contexts=st.lists(structured_context_strategy(), min_size=2, max_size=5))
    @pytest.mark.property
    def test_ranking_stability_and_determinism(self, contexts):
        """
        Property test: For any set of disasters, ranking should be stable 
        and deterministic across multiple calls.
        """
        prioritizer = AlertPrioritizer()

        # Ensure unique disaster IDs
        for i, context in enumerate(contexts):
            context.disaster_info.disaster_id = f"stable-test-{i}"

        # Rank disasters multiple times
        ranking1 = prioritizer.rank_concurrent_disasters(contexts)
        ranking2 = prioritizer.rank_concurrent_disasters(contexts)

        # Results should be identical
        assert len(ranking1) == len(ranking2)

        for rd1, rd2 in zip(ranking1, ranking2):
            assert rd1.disaster_id == rd2.disaster_id
            assert rd1.rank == rd2.rank
            assert abs(rd1.priority.score - rd2.priority.score) < 0.001
            assert abs(rd1.comparative_urgency -
                       rd2.comparative_urgency) < 0.001
            assert rd1.priority.level == rd2.priority.level

    @given(contexts=st.lists(structured_context_strategy(), min_size=1, max_size=5))
    @pytest.mark.property
    def test_fallback_priority_handling(self, contexts):
        """
        Property test: For any disasters where priority analysis fails, 
        the system should use fallback HIGH priority with proper logging.
        """
        prioritizer = AlertPrioritizer()

        # Ensure unique disaster IDs
        for i, context in enumerate(contexts):
            context.disaster_info.disaster_id = f"fallback-test-{i}"

        # Mock analyze_priority to fail for some disasters
        original_analyze = prioritizer.analyze_priority

        def mock_analyze_priority(context):
            # Fail for disasters with even indices
            disaster_num = int(
                context.disaster_info.disaster_id.split('-')[-1])
            if disaster_num % 2 == 0:
                raise Exception(
                    f"Simulated failure for {context.disaster_info.disaster_id}")
            return original_analyze(context)

        with patch.object(prioritizer, 'analyze_priority', side_effect=mock_analyze_priority):
            ranked_disasters = prioritizer.rank_concurrent_disasters(contexts)

        # All disasters should still be ranked (with fallbacks)
        assert len(ranked_disasters) == len(contexts)

        # Check that fallback priorities were used appropriately
        for i, disaster in enumerate(ranked_disasters):
            disaster_num = int(disaster.disaster_id.split('-')[-1])
            if disaster_num % 2 == 0:  # Should have used fallback
                assert "FALLBACK" in disaster.priority.reasoning
                assert disaster.priority.level == PriorityLevel.HIGH
                assert disaster.priority.score == 0.75  # Default fallback score
            # Successful analysis disasters should not have fallback reasoning
            else:
                assert "FALLBACK" not in disaster.priority.reasoning

    @given(contexts=st.lists(structured_context_strategy(), min_size=1, max_size=3))
    @pytest.mark.property
    def test_priority_statistics_consistency(self, contexts):
        """
        Property test: For any set of ranked disasters, priority statistics 
        should be mathematically consistent and complete.
        """
        prioritizer = AlertPrioritizer()

        # Ensure unique disaster IDs
        for i, context in enumerate(contexts):
            context.disaster_info.disaster_id = f"stats-test-{i}"

        ranked_disasters = prioritizer.rank_concurrent_disasters(contexts)
        stats = prioritizer.get_priority_statistics(ranked_disasters)

        # Validate basic statistics structure
        assert "total_disasters" in stats
        assert "priority_distribution" in stats
        assert "score_statistics" in stats
        assert "fallback_count" in stats
        assert "fallback_percentage" in stats

        # Validate counts
        assert stats["total_disasters"] == len(contexts)

        # Validate priority distribution sums to total
        distribution_sum = sum(stats["priority_distribution"].values())
        assert distribution_sum == len(contexts)

        # Validate score statistics
        scores = [rd.priority.score for rd in ranked_disasters]
        assert abs(stats["score_statistics"]["average"] -
                   (sum(scores) / len(scores))) < 0.001
        assert stats["score_statistics"]["maximum"] == max(scores)
        assert stats["score_statistics"]["minimum"] == min(scores)

        # Validate fallback percentage calculation
        fallback_count = sum(
            1 for rd in ranked_disasters if "FALLBACK" in rd.priority.reasoning)
        expected_percentage = (fallback_count / len(contexts)) * 100
        assert abs(stats["fallback_percentage"] - expected_percentage) < 0.001

        # Validate highest/lowest priority disaster identification
        if ranked_disasters:
            assert stats["highest_priority_disaster"] == ranked_disasters[0].disaster_id
            assert stats["lowest_priority_disaster"] == ranked_disasters[-1].disaster_id

    @given(context=structured_context_strategy())
    @pytest.mark.property
    def test_fallback_priority_creation_consistency(self, context):
        """
        Property test: For any context where priority analysis fails, 
        fallback priority should be consistently created with HIGH level.
        """
        prioritizer = AlertPrioritizer()

        # Test analyze_priority_with_fallback
        with patch.object(prioritizer, 'analyze_priority', side_effect=Exception("Test failure")):
            fallback_priority = prioritizer.analyze_priority_with_fallback(
                context)

        # Validate fallback priority properties
        assert isinstance(fallback_priority, AlertPriority)
        assert fallback_priority.level == PriorityLevel.HIGH
        assert fallback_priority.score == 0.75
        assert "FALLBACK" in fallback_priority.reasoning
        assert fallback_priority.estimated_response_time == timedelta(
            minutes=15)
        assert fallback_priority.confidence == 0.5

        # Test direct fallback creation
        test_reasoning = "Test fallback reasoning"
        direct_fallback = prioritizer._create_fallback_priority(test_reasoning)

        assert direct_fallback.level == PriorityLevel.HIGH
        assert direct_fallback.score == 0.75
        assert test_reasoning in direct_fallback.reasoning
        assert "FALLBACK" in direct_fallback.reasoning
