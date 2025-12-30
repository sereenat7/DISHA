"""
Simple property-based tests for Context Builder component.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from unittest.mock import patch

from agentic_disaster_response.context_builder import ContextBuilder, ContextValidationError
from agentic_disaster_response.models.disaster_data import (
    DisasterData, DisasterType, SeverityLevel, GeographicalArea, ImpactAssessment
)
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.context import StructuredContext


@st.composite
def simple_disaster_data(draw):
    """Generate simple valid DisasterData objects."""
    disaster_id = draw(st.text(min_size=1, max_size=20))
    disaster_type = draw(st.sampled_from(DisasterType))
    location = Location(
        latitude=draw(st.floats(min_value=-90, max_value=90)),
        longitude=draw(st.floats(min_value=-180, max_value=180))
    )
    severity = draw(st.sampled_from(SeverityLevel))

    affected_area = GeographicalArea(
        center=location,
        radius_km=draw(st.floats(min_value=0.1, max_value=10.0))
    )

    impact = ImpactAssessment(
        estimated_affected_population=draw(
            st.integers(min_value=1, max_value=10000))
    )

    return DisasterData(
        disaster_id=disaster_id,
        disaster_type=disaster_type,
        location=location,
        severity=severity,
        timestamp=datetime.now(),
        affected_areas=[affected_area],
        estimated_impact=impact
    )


@given(disaster_data=simple_disaster_data())
@settings(max_examples=10, deadline=5000)
@pytest.mark.asyncio
async def test_property_4_context_enrichment_completeness(disaster_data):
    """
    Property 4: Context Enrichment Completeness

    For any disaster data, the Context Builder should enrich it with geographical 
    context, integrate evacuation route information, and structure the result 
    in a standardized format.

    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    context_builder = ContextBuilder(
        search_radius_km=10.0, max_routes_per_category=3)

    mock_evacuation_routes = {
        "alert_id": "test-alert-123",
        "results": {
            "user_position": {"lat": 52.5200, "lon": 13.4050},
            "search_radius_km": 10.0,
            "routes": {
                "hospitals": [
                    {
                        "safe_location": "Test Hospital",
                        "lat": 52.5300,
                        "lon": 13.4100,
                        "distance_km": 1.5,
                        "route": {
                            "duration_s": 300,
                            "geometry": [[13.4050, 52.5200], [13.4100, 52.5300]]
                        }
                    }
                ],
                "bunkers_shelters": [],
                "underground_parking": []
            }
        }
    }

    mock_safe_locations = [
        {
            "name": "Test Hospital",
            "lat": 52.5300,
            "lon": 13.4100,
            "category": "hospitals",
            "distance_km": 1.5
        }
    ]

    # Mock external API calls
    with patch('agentic_disaster_response.context_builder.find_evacuation_routes') as mock_routes, \
            patch('agentic_disaster_response.context_builder.get_safe_locations') as mock_locations:

        mock_routes.return_value = mock_evacuation_routes
        mock_locations.return_value = mock_safe_locations

        # Build context from disaster data
        context = await context_builder.build_context(disaster_data)

        # Verify context is properly structured
        assert isinstance(context, StructuredContext)
        assert context.disaster_info == disaster_data

        # Verify geographical context enrichment (Requirement 2.1)
        assert context.geographical_context is not None
        assert len(context.geographical_context.affected_areas) > 0
        assert context.geographical_context.safe_locations is not None

        # Verify evacuation route integration (Requirement 2.2)
        assert context.evacuation_routes is not None

        # Verify standardized format structure (Requirement 2.3)
        assert hasattr(context, 'disaster_info')
        assert hasattr(context, 'geographical_context')
        assert hasattr(context, 'evacuation_routes')
        assert hasattr(context, 'affected_population')
        assert hasattr(context, 'available_resources')
        assert hasattr(context, 'risk_assessment')
        assert hasattr(context, 'context_completeness')
        assert hasattr(context, 'missing_data_indicators')

        # Verify population assessment
        assert context.affected_population.total_population > 0
        assert context.affected_population.vulnerable_population >= 0

        # Verify resource inventory
        assert context.available_resources.available_shelters >= 0
        assert context.available_resources.shelter_capacity >= 0

        # Verify risk assessment
        assert 0.0 <= context.risk_assessment.overall_risk_score <= 1.0
        assert 0.0 <= context.risk_assessment.evacuation_difficulty <= 1.0
        assert 0.0 <= context.risk_assessment.time_criticality <= 1.0
        assert 0.0 <= context.risk_assessment.resource_availability <= 1.0

        # Verify context completeness
        assert 0.0 <= context.context_completeness <= 1.0
        assert isinstance(context.missing_data_indicators, list)


@given(disaster_data=simple_disaster_data())
@settings(max_examples=10, deadline=5000)
@pytest.mark.asyncio
async def test_property_5_partial_context_handling(disaster_data):
    """
    Property 5: Partial Context Handling

    For any context building failure, the system should provide partial context 
    with clear indicators of missing information and validate complete contexts 
    before proceeding.

    **Validates: Requirements 2.4, 2.5**
    """
    context_builder = ContextBuilder(
        search_radius_km=10.0, max_routes_per_category=3)

    # Mock external API calls to simulate failures/partial data
    with patch('agentic_disaster_response.context_builder.find_evacuation_routes') as mock_routes, \
            patch('agentic_disaster_response.context_builder.get_safe_locations') as mock_locations:

        # Simulate partial failure - no evacuation routes
        mock_routes.return_value = {
            "alert_id": "test-alert-123",
            "results": {
                "user_position": {"lat": 52.5200, "lon": 13.4050},
                "search_radius_km": 10.0,
                "routes": {
                    "hospitals": [],
                    "bunkers_shelters": [],
                    "underground_parking": []
                }
            }
        }

        # Simulate partial failure - no safe locations
        mock_locations.return_value = []

        # Build context with partial data
        context = await context_builder.build_context(disaster_data)

        # Verify partial context handling (Requirement 2.4)
        assert isinstance(context, StructuredContext)
        assert context.context_completeness < 1.0  # Should indicate incompleteness
        # Should have missing data indicators
        assert len(context.missing_data_indicators) > 0

        # Verify missing data indicators are meaningful
        missing_indicators = context.missing_data_indicators
        assert isinstance(missing_indicators, list)

        # Verify context validation still passes (Requirement 2.5)
        # The context should be valid even if incomplete
        try:
            context_builder._validate_context(context)
            validation_passed = True
        except ContextValidationError:
            validation_passed = False

        # Context should either pass validation or have completeness >= 0.3
        # (below 0.3 with critical missing data should fail validation)
        if not validation_passed:
            assert context.context_completeness < 0.3
            critical_missing = [
                indicator for indicator in missing_indicators
                if any(critical in indicator for critical in ['safe_locations', 'evacuation_routes'])
            ]
            assert len(critical_missing) > 0
        else:
            # If validation passed, context should be usable
            assert context.context_completeness >= 0.0
            assert context.disaster_info is not None
            assert context.geographical_context is not None
            assert context.affected_population is not None
            assert context.available_resources is not None
            assert context.risk_assessment is not None
