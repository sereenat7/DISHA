"""
Tests for the health check endpoint with impact radius system status.
"""

import pytest
from fastapi.testclient import TestClient
from app import app


class TestHealthCheck:
    """Test the health check endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_health_check_structure(self, client):
        """
        Test that health check endpoint returns correct structure.
        
        Verifies:
        1. Endpoint returns 200 OK
        2. Response includes all required fields
        3. Impact radius system status is included
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "twilio_configured" in data
        assert "overpass_osrm_reachable" in data
        assert "impact_radius_system" in data
        assert "timestamp" in data
    
    def test_health_check_impact_radius_system(self, client):
        """
        Test that impact radius system status is properly reported.
        
        Verifies:
        1. ML models availability is reported
        2. Supported disaster types are listed
        3. System status is reported
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify impact radius system structure
        impact_system = data["impact_radius_system"]
        assert "ml_models_available" in impact_system
        assert "supported_disaster_types" in impact_system
        assert "status" in impact_system
        
        # Verify ML models availability is a dictionary
        assert isinstance(impact_system["ml_models_available"], dict)
        
        # Verify supported disaster types
        supported_types = impact_system["supported_disaster_types"]
        assert isinstance(supported_types, list)
        assert "earthquake" in supported_types
        assert "flood" in supported_types
        assert "fire" in supported_types
        assert "cyclone" in supported_types
        assert "gas_leak" in supported_types
        
        # Verify system status
        assert impact_system["status"] == "ready"
    
    def test_health_check_ml_models_loaded(self, client):
        """
        Test that ML models are reported as loaded.
        
        Verifies that ML model availability is properly reported.
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        impact_system = data["impact_radius_system"]
        ml_models = impact_system["ml_models_available"]
        
        # ML models should be a dictionary
        assert isinstance(ml_models, dict)
        
        # Should have entries for all disaster types
        assert "earthquake" in ml_models
        assert "flood" in ml_models
        assert "fire" in ml_models
        assert "cyclone" in ml_models
        assert "gas_leak" in ml_models
        
        # Each entry should be a boolean
        for disaster_type, available in ml_models.items():
            assert isinstance(available, bool)
    
    def test_health_check_system_readiness(self, client):
        """
        Test that system readiness is properly reported.
        
        Verifies that the impact radius system reports as ready.
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # System should be ready
        impact_system = data["impact_radius_system"]
        assert impact_system["status"] == "ready"
        
        # Should support all disaster types
        assert len(impact_system["supported_disaster_types"]) == 5
    
    def test_health_check_timestamp(self, client):
        """
        Test that health check includes a timestamp.
        
        Verifies that timestamp is in ISO format.
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamp exists and is a string
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        
        # Verify timestamp is in ISO format (basic check)
        assert "T" in data["timestamp"]  # ISO format includes 'T' separator
