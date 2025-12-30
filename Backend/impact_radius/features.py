"""
Feature definitions, validation rules, and disaster type constants.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class DisasterType(str, Enum):
    """Supported disaster types."""
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    FIRE = "fire"
    CYCLONE = "cyclone"
    GAS_LEAK = "gas_leak"


# Disaster-specific feature requirements
REQUIRED_FEATURES: Dict[DisasterType, List[str]] = {
    DisasterType.FLOOD: ["rainfall_intensity", "duration", "elevation", "river_proximity"],
    DisasterType.EARTHQUAKE: ["magnitude", "depth", "soil_type"],
    DisasterType.FIRE: ["fire_intensity", "wind_speed", "wind_direction", "humidity", "temperature"],
    DisasterType.CYCLONE: ["wind_speed", "atmospheric_pressure", "movement_speed", "coastal_proximity"],
    DisasterType.GAS_LEAK: ["wind_speed", "atmospheric_stability", "leak_severity"],
}


# Feature value bounds (min, max) for validation
FEATURE_BOUNDS: Dict[str, tuple] = {
    # Flood features
    "rainfall_intensity": (0.0, 500.0),  # mm/hour
    "duration": (0.0, 168.0),  # hours (max 7 days)
    "elevation": (-500.0, 9000.0),  # meters (Dead Sea to Everest)
    "river_proximity": (0.0, 100.0),  # km
    
    # Earthquake features
    "magnitude": (0.0, 10.0),  # Richter scale
    "depth": (0.0, 700.0),  # km
    "soil_type": (1.0, 5.0),  # categorical: 1=rock, 2=dense_soil, 3=soft_soil, 4=sand, 5=fill
    
    # Fire features
    "fire_intensity": (0.0, 100.0),  # arbitrary scale 0-100
    "wind_speed": (0.0, 200.0),  # km/h
    "wind_direction": (0.0, 360.0),  # degrees
    "humidity": (0.0, 100.0),  # percentage
    "temperature": (-50.0, 60.0),  # Celsius
    
    # Cyclone features
    "atmospheric_pressure": (870.0, 1050.0),  # hPa
    "movement_speed": (0.0, 100.0),  # km/h
    "coastal_proximity": (0.0, 1000.0),  # km
    
    # Gas leak features
    "atmospheric_stability": (1.0, 6.0),  # Pasquill stability class (1=A very unstable, 6=F very stable)
    "leak_severity": (1.0, 10.0),  # arbitrary scale 1-10
}


# Realistic radius bounds per disaster type (km)
RADIUS_BOUNDS: Dict[DisasterType, tuple] = {
    DisasterType.FLOOD: (0.5, 100.0),
    DisasterType.EARTHQUAKE: (1.0, 500.0),
    DisasterType.FIRE: (0.1, 50.0),
    DisasterType.CYCLONE: (10.0, 500.0),
    DisasterType.GAS_LEAK: (0.1, 10.0),
}


class FeatureValidationError(ValueError):
    """Raised when feature validation fails."""
    pass


def validate_features(disaster_type: DisasterType, features: Dict[str, float]) -> None:
    """
    Validate that all required features are present and within valid ranges.
    
    Args:
        disaster_type: The type of disaster
        features: Dictionary of feature names to values
        
    Raises:
        FeatureValidationError: If validation fails
    """
    # Check for missing required features
    required = REQUIRED_FEATURES[disaster_type]
    missing = [f for f in required if f not in features]
    if missing:
        raise FeatureValidationError(
            f"Missing required features for {disaster_type.value}: {missing}"
        )
    
    # Check feature value ranges
    for feature_name, value in features.items():
        if feature_name in FEATURE_BOUNDS:
            min_val, max_val = FEATURE_BOUNDS[feature_name]
            if not (min_val <= value <= max_val):
                raise FeatureValidationError(
                    f"Feature '{feature_name}' value {value} is out of valid range [{min_val}, {max_val}]"
                )


class ImpactRadiusPredictionRequest(BaseModel):
    """Request model for impact radius prediction."""
    
    disaster_type: DisasterType = Field(
        ...,
        description="Type of disaster"
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude of disaster epicenter"
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude of disaster epicenter"
    )
    features: Dict[str, float] = Field(
        ...,
        description="Disaster-specific features extracted from external data sources"
    )
    
    @model_validator(mode='after')
    def validate_disaster_features(self):
        """Validate that required features are present and within bounds."""
        validate_features(self.disaster_type, self.features)
        return self
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "disaster_type": "earthquake",
                    "latitude": 34.05,
                    "longitude": -118.25,
                    "features": {
                        "magnitude": 6.5,
                        "depth": 10.0,
                        "soil_type": 3.0
                    }
                }
            ]
        }
    }


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MethodUsed(str, Enum):
    """Prediction method indicator."""
    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry for circular threat zone."""
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]


class GeoJSONProperties(BaseModel):
    """GeoJSON properties for threat zone."""
    radius_km: float
    risk_level: RiskLevel
    disaster_type: str


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature structure."""
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONProperties


class ImpactRadiusPredictionResponse(BaseModel):
    """Response model for impact radius prediction."""
    
    radius_km: float = Field(
        ...,
        gt=0.0,
        description="Predicted impact radius in kilometers"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk level classification"
    )
    method_used: MethodUsed = Field(
        ...,
        description="Prediction method used"
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Human-readable explanation of the prediction"
    )
    epicenter: Dict[str, float] = Field(
        ...,
        description="Disaster epicenter coordinates"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of prediction generation"
    )
    geojson: GeoJSONFeature = Field(
        ...,
        description="GeoJSON representation for map visualization"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "radius_km": 15.5,
                    "confidence_score": 0.85,
                    "risk_level": "high",
                    "method_used": "hybrid",
                    "explanation": "Earthquake magnitude 6.5 at shallow depth (10km) in soft soil area. Hybrid prediction combining rule-based (60%) and ML model (40%).",
                    "epicenter": {"latitude": 34.05, "longitude": -118.25},
                    "timestamp": "2024-01-15T10:30:00Z",
                    "geojson": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-118.25, 34.05]
                        },
                        "properties": {
                            "radius_km": 15.5,
                            "risk_level": "high",
                            "disaster_type": "earthquake"
                        }
                    }
                }
            ]
        }
    }
