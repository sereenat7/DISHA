"""
Pytest configuration and fixtures for disaster response tests.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from agentic_disaster_response.models import (
    DisasterData, DisasterType, SeverityLevel, Location,
    ImpactAssessment, GeographicalArea, AlertPriority, PriorityLevel
)
from agentic_disaster_response.core import setup_logging


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Set up logging for tests."""
    setup_logging(log_level="DEBUG", enable_console=False)


@pytest.fixture
def sample_location():
    """Sample location for testing."""
    return Location(
        latitude=19.0760,
        longitude=72.8777,
        address="Mumbai, Maharashtra, India",
        administrative_area="Maharashtra",
        country="India"
    )


@pytest.fixture
def sample_disaster_data(sample_location):
    """Sample disaster data for testing."""
    return DisasterData(
        disaster_id="test-disaster-001",
        disaster_type=DisasterType.FIRE,
        location=sample_location,
        severity=SeverityLevel.HIGH,
        timestamp=datetime.now(),
        affected_areas=[
            GeographicalArea(
                center=sample_location,
                radius_km=5.0,
                area_name="Central Mumbai"
            )
        ],
        estimated_impact=ImpactAssessment(
            estimated_affected_population=10000,
            estimated_casualties=50,
            infrastructure_damage_level=SeverityLevel.MEDIUM
        ),
        description="Test fire disaster",
        source="manual_trigger"
    )


@pytest.fixture
def sample_alert_priority():
    """Sample alert priority for testing."""
    return AlertPriority(
        level=PriorityLevel.HIGH,
        score=0.8,
        reasoning="High population density and limited evacuation routes",
        estimated_response_time=timedelta(minutes=15),
        required_resources=[],
        confidence=0.9
    )


@pytest.fixture
def mock_fastapi_backend():
    """Mock FastAPI backend for testing."""
    mock = AsyncMock()
    mock.get_disaster_data.return_value = {
        "disaster_id": "test-001",
        "type": "fire",
        "location": {"lat": 19.0760, "lon": 72.8777},
        "severity": "high"
    }
    return mock


@pytest.fixture
def mock_evacuation_system():
    """Mock evacuation system for testing."""
    mock = AsyncMock()
    mock.find_evacuation_routes.return_value = {
        "alert_id": "test-alert-001",
        "results": {
            "user_position": {"lat": 19.0760, "lon": 72.8777},
            "search_radius_km": 10.0,
            "routes": {
                "hospitals": [
                    {
                        "safe_location": "Test Hospital",
                        "lat": 19.0800,
                        "lon": 72.8800,
                        "distance_km": 2.5,
                        "route": {
                            "distance_m": 2500,
                            "duration_s": 300,
                            "geometry": [[72.8777, 19.0760], [72.8800, 19.0800]]
                        }
                    }
                ],
                "bunkers_shelters": [],
                "underground_parking": []
            }
        }
    }
    return mock


@pytest.fixture
def mock_mcp_tool():
    """Mock MCP tool for testing."""
    mock = AsyncMock()
    mock.execute.return_value = {
        "status": "success",
        "message": "Alert dispatched successfully",
        "recipients": 100,
        "delivered": 95
    }
    return mock


# Property-based testing settings
@pytest.fixture
def hypothesis_settings():
    """Hypothesis settings for property-based tests."""
    from hypothesis import settings, Verbosity
    return settings(
        max_examples=100,
        verbosity=Verbosity.verbose,
        deadline=timedelta(seconds=10)
    )
