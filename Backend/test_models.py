#!/usr/bin/env python3
"""
Test script to verify ML models are working correctly.
"""

import sys
from impact_radius.predictor import ImpactRadiusPredictor
from impact_radius.features import DisasterType

def test_models():
    """Test all ML models with sample data."""
    
    print("=" * 60)
    print("Testing ML Models")
    print("=" * 60)
    
    # Initialize predictor
    predictor = ImpactRadiusPredictor()
    
    # Check system status
    status = predictor.get_system_status()
    print(f"\nSystem Status:")
    print(f"  ML Models Available: {status['ml_models_available']}")
    print(f"  Supported Types: {status['supported_disaster_types']}")
    print(f"  Status: {status['status']}")
    
    # Test cases for each disaster type
    test_cases = [
        {
            "name": "Earthquake",
            "disaster_type": DisasterType.EARTHQUAKE,
            "latitude": 34.05,
            "longitude": -118.25,
            "features": {
                "magnitude": 6.5,
                "depth": 10.0,
                "soil_type": 3.0
            }
        },
        {
            "name": "Flood",
            "disaster_type": DisasterType.FLOOD,
            "latitude": 19.1337,
            "longitude": 72.8611,
            "features": {
                "rainfall_intensity": 50.0,
                "duration": 12.0,
                "elevation": 10.0,
                "river_proximity": 2.0
            }
        },
        {
            "name": "Fire",
            "disaster_type": DisasterType.FIRE,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "features": {
                "fire_intensity": 75.0,
                "wind_speed": 30.0,
                "wind_direction": 180.0,
                "humidity": 20.0,
                "temperature": 35.0
            }
        },
        {
            "name": "Cyclone",
            "disaster_type": DisasterType.CYCLONE,
            "latitude": 20.0,
            "longitude": 85.0,
            "features": {
                "wind_speed": 150.0,
                "atmospheric_pressure": 950.0,
                "movement_speed": 20.0,
                "coastal_proximity": 50.0
            }
        },
        {
            "name": "Gas Leak",
            "disaster_type": DisasterType.GAS_LEAK,
            "latitude": 28.6139,
            "longitude": 77.2090,
            "features": {
                "wind_speed": 15.0,
                "atmospheric_stability": 3.0,
                "leak_severity": 7.0
            }
        }
    ]
    
    print("\n" + "=" * 60)
    print("Testing Predictions")
    print("=" * 60)
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        print(f"  Location: ({test_case['latitude']}, {test_case['longitude']})")
        print(f"  Features: {test_case['features']}")
        
        try:
            # Make prediction
            result = predictor.predict(
                disaster_type=test_case['disaster_type'],
                latitude=test_case['latitude'],
                longitude=test_case['longitude'],
                features=test_case['features']
            )
            
            # Check if ML model was used
            ml_available = predictor.ml_predictor.is_model_available(test_case['disaster_type'])
            
            print(f"  ✓ Prediction successful!")
            print(f"  ML Model Available: {ml_available}")
            print(f"  Method Used: {result.method_used.value}")
            print(f"  Radius: {result.radius_km:.2f} km")
            print(f"  Confidence: {result.confidence_score:.2f}")
            print(f"  Risk Level: {result.risk_level.value}")
            
            # Verify ML model is being used if available
            if ml_available and result.method_used.value == "rule_based":
                print(f"  ⚠ WARNING: ML model available but not used!")
                all_passed = False
            
        except Exception as e:
            print(f"  ✗ Prediction failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)
