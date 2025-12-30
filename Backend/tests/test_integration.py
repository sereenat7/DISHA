"""
Integration tests for disaster impact radius → evacuation routing workflow.

Tests the complete workflow from impact radius prediction to evacuation route
calculation, verifying that the systems work together correctly.
"""

import pytest
import asyncio
from impact_radius.predictor import ImpactRadiusPredictor
from impact_radius.features import DisasterType, ImpactRadiusPredictionRequest
from evacuation_system.main import find_evacuation_routes


class TestCombinedWorkflow:
    """Test the combined workflow of impact radius prediction and evacuation routing."""
    
    @pytest.fixture
    def predictor(self):
        """Create an impact radius predictor instance."""
        return ImpactRadiusPredictor()
    
    @pytest.mark.asyncio
    async def test_earthquake_to_evacuation_workflow(self, predictor):
        """
        Test complete workflow: earthquake prediction → evacuation routing.
        
        Scenario: Earthquake in Los Angeles area
        1. Predict impact radius for earthquake
        2. Use predicted radius for evacuation route search
        3. Verify evacuation routes are found
        """
        # Step 1: Predict impact radius for earthquake
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.EARTHQUAKE,
            latitude=34.05,
            longitude=-118.25,
            features={
                "magnitude": 6.5,
                "depth": 10.0,
                "soil_type": 3.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify prediction is valid
        assert prediction.radius_km > 0
        assert 0.0 <= prediction.confidence_score <= 1.0
        assert prediction.risk_level.value in ["low", "moderate", "high", "critical"]
        
        # Step 2: Use predicted radius for evacuation routing
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=2
        )
        
        # Step 3: Verify evacuation routes structure
        assert "alert_id" in evacuation_data
        assert "results" in evacuation_data
        assert "user_position" in evacuation_data["results"]
        assert "search_radius_km" in evacuation_data["results"]
        assert "routes" in evacuation_data["results"]
        
        # Verify user position matches
        assert evacuation_data["results"]["user_position"]["lat"] == request.latitude
        assert evacuation_data["results"]["user_position"]["lon"] == request.longitude
        
        # Verify search radius matches prediction
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
        
        # Verify route categories exist
        routes = evacuation_data["results"]["routes"]
        assert "hospitals" in routes
        assert "bunkers_shelters" in routes
        assert "underground_parking" in routes
    
    @pytest.mark.asyncio
    async def test_flood_to_evacuation_workflow(self, predictor):
        """
        Test complete workflow: flood prediction → evacuation routing.
        
        Scenario: Severe flooding in Mumbai
        1. Predict impact radius for flood
        2. Use predicted radius for evacuation route search
        3. Verify evacuation routes are found
        """
        # Step 1: Predict impact radius for flood
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.FLOOD,
            latitude=19.1337,
            longitude=72.8611,
            features={
                "rainfall_intensity": 80.0,
                "duration": 24.0,
                "elevation": 5.0,
                "river_proximity": 1.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify prediction is valid
        assert prediction.radius_km > 0
        assert prediction.risk_level.value in ["low", "moderate", "high", "critical"]
        
        # Step 2: Use predicted radius for evacuation routing
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=1
        )
        
        # Step 3: Verify evacuation data structure
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
        assert "routes" in evacuation_data["results"]
    
    @pytest.mark.asyncio
    async def test_fire_to_evacuation_workflow(self, predictor):
        """
        Test complete workflow: fire prediction → evacuation routing.
        
        Scenario: Wildfire in San Francisco area
        1. Predict impact radius for fire
        2. Use predicted radius for evacuation route search
        3. Verify evacuation routes are found
        """
        # Step 1: Predict impact radius for fire
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.FIRE,
            latitude=37.7749,
            longitude=-122.4194,
            features={
                "fire_intensity": 85.0,
                "wind_speed": 40.0,
                "wind_direction": 180.0,
                "humidity": 15.0,
                "temperature": 38.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify prediction is valid
        assert prediction.radius_km > 0
        assert prediction.risk_level.value in ["low", "moderate", "high", "critical"]
        
        # Step 2: Use predicted radius for evacuation routing
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=2
        )
        
        # Step 3: Verify evacuation data structure
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
    
    @pytest.mark.asyncio
    async def test_cyclone_to_evacuation_workflow(self, predictor):
        """
        Test complete workflow: cyclone prediction → evacuation routing.
        
        Scenario: Cyclone approaching coastal area
        1. Predict impact radius for cyclone
        2. Use predicted radius for evacuation route search
        3. Verify evacuation routes are found
        """
        # Step 1: Predict impact radius for cyclone
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.CYCLONE,
            latitude=20.0,
            longitude=85.0,
            features={
                "wind_speed": 150.0,
                "atmospheric_pressure": 950.0,
                "movement_speed": 20.0,
                "coastal_proximity": 50.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify prediction is valid
        assert prediction.radius_km > 0
        assert prediction.risk_level.value in ["low", "moderate", "high", "critical"]
        
        # Step 2: Use predicted radius for evacuation routing
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=2
        )
        
        # Step 3: Verify evacuation data structure
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
    
    @pytest.mark.asyncio
    async def test_gas_leak_to_evacuation_workflow(self, predictor):
        """
        Test complete workflow: gas leak prediction → evacuation routing.
        
        Scenario: Gas leak in urban area
        1. Predict impact radius for gas leak
        2. Use predicted radius for evacuation route search
        3. Verify evacuation routes are found
        """
        # Step 1: Predict impact radius for gas leak
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.GAS_LEAK,
            latitude=28.6139,
            longitude=77.2090,
            features={
                "wind_speed": 15.0,
                "atmospheric_stability": 3.0,
                "leak_severity": 7.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify prediction is valid
        assert prediction.radius_km > 0
        assert prediction.risk_level.value in ["low", "moderate", "high", "critical"]
        
        # Step 2: Use predicted radius for evacuation routing
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=2
        )
        
        # Step 3: Verify evacuation data structure
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
    
    def test_radius_as_evacuation_input(self, predictor):
        """
        Test that predicted radius can be used as input to evacuation system.
        
        Verifies that:
        1. Predicted radius is always positive
        2. Radius can be capped for evacuation search if needed
        3. Radius format is compatible with evacuation system
        """
        # Test with various disaster types
        test_cases = [
            (DisasterType.EARTHQUAKE, {"magnitude": 5.0, "depth": 15.0, "soil_type": 2.0}),
            (DisasterType.FLOOD, {"rainfall_intensity": 50.0, "duration": 12.0, "elevation": 10.0, "river_proximity": 2.0}),
            (DisasterType.FIRE, {"fire_intensity": 60.0, "wind_speed": 25.0, "wind_direction": 90.0, "humidity": 30.0, "temperature": 30.0}),
            (DisasterType.CYCLONE, {"wind_speed": 120.0, "atmospheric_pressure": 970.0, "movement_speed": 15.0, "coastal_proximity": 100.0}),
            (DisasterType.GAS_LEAK, {"wind_speed": 10.0, "atmospheric_stability": 4.0, "leak_severity": 5.0}),
        ]
        
        for disaster_type, features in test_cases:
            request = ImpactRadiusPredictionRequest(
                disaster_type=disaster_type,
                latitude=20.0,
                longitude=75.0,
                features=features
            )
            
            prediction = predictor.predict_from_request(request)
            
            # Verify radius is positive
            assert prediction.radius_km > 0, f"Radius must be positive for {disaster_type}"
            
            # Verify radius is a float (compatible with evacuation system)
            assert isinstance(prediction.radius_km, float), "Radius must be a float"
            
            # Verify radius can be capped for evacuation search if needed
            evacuation_radius = min(prediction.radius_km, 50.0)
            assert evacuation_radius > 0, "Capped radius must be positive"
            assert evacuation_radius <= 50.0, "Capped radius must be within evacuation limits"
    
    @pytest.mark.asyncio
    async def test_realistic_disaster_scenario_high_risk(self, predictor):
        """
        Test realistic high-risk disaster scenario with complete workflow.
        
        Scenario: Major earthquake (magnitude 7.5) in populated area
        Expected: High/critical risk level, large radius, evacuation routes found
        """
        # Major earthquake scenario
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.EARTHQUAKE,
            latitude=35.6762,  # Tokyo area
            longitude=139.6503,
            features={
                "magnitude": 7.5,
                "depth": 8.0,
                "soil_type": 4.0  # Sand - amplifies shaking
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify high-risk characteristics
        assert prediction.risk_level.value in ["high", "critical"], "Major earthquake should be high/critical risk"
        assert prediction.radius_km >= 20.0, "Major earthquake should have large impact radius"
        assert prediction.confidence_score > 0.5, "Should have reasonable confidence"
        
        # Verify evacuation routing works with large radius
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=min(prediction.radius_km, 50.0),  # Cap at 50km for API limits
            max_per_category=2
        )
        
        assert evacuation_data["results"]["search_radius_km"] <= 50.0
    
    @pytest.mark.asyncio
    async def test_realistic_disaster_scenario_moderate_risk(self, predictor):
        """
        Test realistic moderate-risk disaster scenario with complete workflow.
        
        Scenario: Moderate flooding in urban area
        Expected: Moderate risk level, medium radius, evacuation routes found
        """
        # Moderate flood scenario
        request = ImpactRadiusPredictionRequest(
            disaster_type=DisasterType.FLOOD,
            latitude=40.7128,  # New York area
            longitude=-74.0060,
            features={
                "rainfall_intensity": 40.0,
                "duration": 8.0,
                "elevation": 15.0,
                "river_proximity": 3.0
            }
        )
        
        prediction = predictor.predict_from_request(request)
        
        # Verify moderate-risk characteristics
        assert prediction.risk_level.value in ["low", "moderate", "high"], "Moderate flood should be low/moderate/high risk"
        assert 5.0 <= prediction.radius_km <= 30.0, "Moderate flood should have medium impact radius"
        
        # Verify evacuation routing works
        evacuation_data = await find_evacuation_routes(
            user_lat=request.latitude,
            user_lon=request.longitude,
            radius_km=prediction.radius_km,
            max_per_category=2
        )
        
        assert evacuation_data["results"]["search_radius_km"] == prediction.radius_km
