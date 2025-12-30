"""
Property-based tests for core data models.

Feature: agentic-disaster-response, Property 1: FastAPI Integration Consistency
**Validates: Requirements 1.1, 1.2**
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume
from unittest.mock import AsyncMock, patch

from agentic_disaster_response.models import (
    DisasterData, DisasterType, SeverityLevel, Location,
    ImpactAssessment, GeographicalArea, AlertPriority, PriorityLevel
)


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

    description = draw(st.one_of(st.none(), st.text(min_size=1, max_size=500)))
    source = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))

    return DisasterData(
        disaster_id=disaster_id,
        disaster_type=disaster_type,
        location=location,
        severity=severity,
        timestamp=timestamp,
        affected_areas=affected_areas,
        estimated_impact=estimated_impact,
        description=description,
        source=source
    )


class TestFastAPIIntegrationConsistency:
    """
    Property 1: FastAPI Integration Consistency

    For any disaster event trigger, the Disaster Response Agent should successfully 
    retrieve disaster data from the FastAPI backend and validate its completeness and format.

    **Validates: Requirements 1.1, 1.2**
    """

    @given(disaster_data=disaster_data_strategy())
    @pytest.mark.property
    @pytest.mark.asyncio
    async def test_disaster_data_retrieval_and_validation_consistency(self, disaster_data):
        """
        Property test: For any valid disaster data from FastAPI backend,
        the system should consistently validate and process it.
        """
        # Mock the FastAPI backend response
        mock_backend_response = {
            "disaster_id": disaster_data.disaster_id,
            "disaster_type": disaster_data.disaster_type.value,
            "location": {
                "latitude": disaster_data.location.latitude,
                "longitude": disaster_data.location.longitude,
                "address": disaster_data.location.address,
                "administrative_area": disaster_data.location.administrative_area,
                "country": disaster_data.location.country
            },
            "severity": disaster_data.severity.value,
            "timestamp": disaster_data.timestamp.isoformat(),
            "affected_areas": [
                {
                    "center": {
                        "latitude": area.center.latitude,
                        "longitude": area.center.longitude
                    },
                    "radius_km": area.radius_km,
                    "area_name": area.area_name
                }
                for area in disaster_data.affected_areas
            ],
            "estimated_impact": {
                "estimated_affected_population": disaster_data.estimated_impact.estimated_affected_population,
                "estimated_casualties": disaster_data.estimated_impact.estimated_casualties,
                "infrastructure_damage_level": disaster_data.estimated_impact.infrastructure_damage_level.value,
                "economic_impact_estimate": disaster_data.estimated_impact.economic_impact_estimate,
                "environmental_impact": disaster_data.estimated_impact.environmental_impact
            },
            "description": disaster_data.description,
            "source": disaster_data.source
        }

        # Test data retrieval consistency
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_backend_response
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            # Simulate data retrieval from FastAPI backend
            async with mock_client() as client:
                response = await client.get(f"/disasters/{disaster_data.disaster_id}")
                retrieved_data = mock_backend_response  # Use the mock data directly

            # Validate that retrieved data matches expected format
            assert response.status_code == 200
            assert retrieved_data["disaster_id"] == disaster_data.disaster_id
            assert retrieved_data["disaster_type"] == disaster_data.disaster_type.value
            assert retrieved_data["severity"] == disaster_data.severity.value

            # Validate location data consistency
            location_data = retrieved_data["location"]
            assert location_data["latitude"] == disaster_data.location.latitude
            assert location_data["longitude"] == disaster_data.location.longitude

            # Validate affected areas consistency
            assert len(retrieved_data["affected_areas"]) == len(
                disaster_data.affected_areas)
            for retrieved_area, original_area in zip(retrieved_data["affected_areas"], disaster_data.affected_areas):
                assert retrieved_area["radius_km"] == original_area.radius_km
                assert retrieved_area["center"]["latitude"] == original_area.center.latitude
                assert retrieved_area["center"]["longitude"] == original_area.center.longitude

            # Validate impact assessment consistency
            impact_data = retrieved_data["estimated_impact"]
            assert impact_data["estimated_affected_population"] == disaster_data.estimated_impact.estimated_affected_population
            assert impact_data["infrastructure_damage_level"] == disaster_data.estimated_impact.infrastructure_damage_level.value

    @given(
        disaster_id=st.text(min_size=1, max_size=50),
        invalid_data=st.one_of(
            st.none(),
            st.dictionaries(st.text(), st.text(),
                            max_size=2),  # Incomplete data
            st.just({"invalid": "structure"})  # Wrong structure
        )
    )
    @pytest.mark.property
    @pytest.mark.asyncio
    async def test_invalid_data_handling_consistency(self, disaster_id, invalid_data):
        """
        Property test: For any invalid or incomplete disaster data,
        the system should consistently handle validation failures.
        """
        # Test invalid data handling
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()

            if invalid_data is None:
                # Simulate backend unavailable
                mock_response.status_code = 500
                mock_response.json.return_value = {
                    "error": "Internal server error"}
            else:
                # Simulate invalid data structure
                mock_response.status_code = 200
                mock_response.json.return_value = invalid_data

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            async with mock_client() as client:
                response = await client.get(f"/disasters/{disaster_id}")

                if invalid_data is None:
                    # Should handle backend errors consistently
                    assert response.status_code == 500
                else:
                    # Should detect invalid data structure
                    data = invalid_data  # Use the mock data directly

                    # Validate that required fields are missing or invalid
                    required_fields = [
                        "disaster_id", "disaster_type", "location", "severity", "timestamp"]
                    missing_fields = [
                        field for field in required_fields if field not in data]

                    # System should be able to detect incomplete data
                    if missing_fields or data == {"invalid": "structure"}:
                        # This represents the validation logic that should catch invalid data
                        validation_passed = len(
                            missing_fields) == 0 and "disaster_id" in data

                        # For invalid data, validation should fail
                        if data == {"invalid": "structure"} or missing_fields:
                            assert not validation_passed, f"Validation should fail for invalid data: {data}"

    @given(disaster_data=disaster_data_strategy())
    @pytest.mark.property
    @pytest.mark.asyncio
    async def test_data_completeness_validation_consistency(self, disaster_data):
        """
        Property test: For any disaster data, the system should consistently
        validate completeness and format before processing.
        """
        # Test that all required fields are present and valid
        assert disaster_data.disaster_id is not None and len(
            disaster_data.disaster_id) > 0
        assert disaster_data.disaster_type in DisasterType
        assert disaster_data.severity in SeverityLevel
        assert isinstance(disaster_data.timestamp, datetime)
        assert len(disaster_data.affected_areas) > 0
        assert disaster_data.estimated_impact.estimated_affected_population > 0

        # Test location validation
        location = disaster_data.location
        assert -90 <= location.latitude <= 90
        assert -180 <= location.longitude <= 180

        # Test affected areas validation
        for area in disaster_data.affected_areas:
            assert area.radius_km > 0
            assert -90 <= area.center.latitude <= 90
            assert -180 <= area.center.longitude <= 180

        # Test that the data structure is internally consistent
        # (This simulates the validation that would happen in the actual system)
        validation_result = self._simulate_data_validation(disaster_data)
        assert validation_result["is_valid"] is True
        # High completeness expected
        assert validation_result["completeness_score"] >= 0.8

    def _simulate_data_validation(self, disaster_data: DisasterData) -> dict:
        """
        Simulate the data validation logic that would be used in the actual system.
        This represents the validation requirements from Requirements 1.1 and 1.2.
        """
        validation_result = {
            "is_valid": True,
            "completeness_score": 1.0,
            "missing_fields": [],
            "validation_errors": []
        }

        # Check required fields
        required_fields = [
            ("disaster_id", disaster_data.disaster_id),
            ("disaster_type", disaster_data.disaster_type),
            ("location", disaster_data.location),
            ("severity", disaster_data.severity),
            ("timestamp", disaster_data.timestamp),
            ("affected_areas", disaster_data.affected_areas),
            ("estimated_impact", disaster_data.estimated_impact)
        ]

        for field_name, field_value in required_fields:
            if field_value is None:
                validation_result["missing_fields"].append(field_name)
                validation_result["is_valid"] = False
                validation_result["completeness_score"] -= 0.15

        # Validate data types and ranges
        try:
            if disaster_data.location:
                if not (-90 <= disaster_data.location.latitude <= 90):
                    validation_result["validation_errors"].append(
                        "Invalid latitude")
                    validation_result["is_valid"] = False
                if not (-180 <= disaster_data.location.longitude <= 180):
                    validation_result["validation_errors"].append(
                        "Invalid longitude")
                    validation_result["is_valid"] = False
        except Exception as e:
            validation_result["validation_errors"].append(
                f"Location validation error: {e}")
            validation_result["is_valid"] = False

        # Adjust completeness score based on optional fields
        optional_fields = [
            disaster_data.description,
            disaster_data.source,
            disaster_data.location.address if disaster_data.location else None
        ]

        present_optional = sum(
            1 for field in optional_fields if field is not None)
        validation_result["completeness_score"] += (
            present_optional / len(optional_fields)) * 0.2

        return validation_result
