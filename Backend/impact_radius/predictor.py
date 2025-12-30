"""
Main prediction orchestrator for disaster impact radius.

Coordinates the complete prediction pipeline: validation → rule engine → 
ML model → ensemble combination → GeoJSON output generation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from .features import (
    DisasterType,
    ImpactRadiusPredictionRequest,
    ImpactRadiusPredictionResponse,
    RiskLevel,
    MethodUsed,
    GeoJSONFeature,
    GeoJSONGeometry,
    GeoJSONProperties,
    validate_features,
    FeatureValidationError,
    RADIUS_BOUNDS,
)
from .rule_engine import RuleEngine
from .ml_models import MLModelPredictor
from .ensemble import EnsembleCombiner


logger = logging.getLogger(__name__)


class ImpactRadiusPredictor:
    """
    Main orchestrator for disaster impact radius prediction.
    
    Implements the complete prediction pipeline:
    1. Validate input features
    2. Get rule-based prediction
    3. Get ML-based prediction (if available)
    4. Combine predictions using ensemble logic
    5. Calculate confidence score
    6. Classify risk level
    7. Generate explanation
    8. Create GeoJSON output
    9. Enforce realistic bounds
    """
    
    def __init__(self, models_dir: str = None):
        """
        Initialize the impact radius predictor.
        
        Args:
            models_dir: Directory containing trained ML models.
                       If None, uses the default path relative to the module.
        """
        self.rule_engine = RuleEngine()
        self.ml_predictor = MLModelPredictor(models_dir=models_dir)
        self.ensemble_combiner = EnsembleCombiner()
        
        logger.info("ImpactRadiusPredictor initialized")
        logger.info(f"ML models available: {self.ml_predictor.get_available_models()}")
    
    def predict(
        self,
        disaster_type: DisasterType,
        latitude: float,
        longitude: float,
        features: Dict[str, float]
    ) -> ImpactRadiusPredictionResponse:
        """
        Predict impact radius for a disaster.
        
        Args:
            disaster_type: Type of disaster
            latitude: Latitude of disaster epicenter (-90 to 90)
            longitude: Longitude of disaster epicenter (-180 to 180)
            features: Dictionary of disaster-specific features
            
        Returns:
            Complete prediction response with radius, confidence, risk level, etc.
            
        Raises:
            FeatureValidationError: If features are invalid or incomplete
            ValueError: If coordinates are out of valid range
        """
        try:
            # Step 1: Validate coordinates
            self._validate_coordinates(latitude, longitude)
            
            # Step 2: Validate features
            validate_features(disaster_type, features)
            
            # Calculate feature completeness (for confidence calculation)
            feature_completeness = 1.0  # All required features present
            
            # Step 3: Get rule-based prediction
            logger.debug(f"Getting rule-based prediction for {disaster_type}")
            rule_prediction = self.rule_engine.predict(disaster_type, features)
            
            # Step 4: Get ML-based prediction (if available)
            ml_available = self.ml_predictor.is_model_available(disaster_type)
            if ml_available:
                logger.debug(f"Getting ML prediction for {disaster_type}")
                ml_prediction = self.ml_predictor.predict(
                    disaster_type, 
                    features, 
                    use_fallback=False
                )
            else:
                logger.debug(f"ML model not available for {disaster_type}, using rule-based only")
                ml_prediction = rule_prediction
            
            # Step 5: Combine predictions using ensemble logic
            final_radius, rule_weight, ml_weight, method_used = self.ensemble_combiner.combine_predictions(
                disaster_type=disaster_type,
                rule_prediction=rule_prediction,
                ml_prediction=ml_prediction,
                ml_available=ml_available,
                features=features,
                feature_completeness=feature_completeness
            )
            
            # Step 6: Enforce realistic bounds
            final_radius = self._enforce_bounds(disaster_type, final_radius)
            
            # Step 7: Calculate confidence score
            confidence_score = self.ensemble_combiner.calculate_confidence(
                disaster_type=disaster_type,
                rule_prediction=rule_prediction,
                ml_prediction=ml_prediction,
                ml_available=ml_available,
                feature_completeness=feature_completeness,
                rule_weight=rule_weight,
                ml_weight=ml_weight
            )
            
            # Step 8: Classify risk level
            risk_level = self.ensemble_combiner.classify_risk_level(
                disaster_type=disaster_type,
                radius_km=final_radius,
                features=features
            )
            
            # Step 9: Generate explanation
            explanation = self.ensemble_combiner.generate_explanation(
                disaster_type=disaster_type,
                radius_km=final_radius,
                confidence_score=confidence_score,
                risk_level=risk_level,
                method_used=method_used,
                rule_weight=rule_weight,
                ml_weight=ml_weight,
                features=features
            )
            
            # Step 10: Generate GeoJSON output
            geojson = self._create_geojson(
                latitude=latitude,
                longitude=longitude,
                radius_km=final_radius,
                risk_level=risk_level,
                disaster_type=disaster_type
            )
            
            # Step 11: Create response
            timestamp = datetime.now(timezone.utc).isoformat()
            
            response = ImpactRadiusPredictionResponse(
                radius_km=final_radius,
                confidence_score=confidence_score,
                risk_level=risk_level,
                method_used=method_used,
                explanation=explanation,
                epicenter={"latitude": latitude, "longitude": longitude},
                timestamp=timestamp,
                geojson=geojson
            )
            
            logger.info(
                f"Prediction complete: {disaster_type.value} at ({latitude}, {longitude}), "
                f"radius={final_radius:.2f}km, confidence={confidence_score:.2f}, "
                f"risk={risk_level.value}"
            )
            
            return response
            
        except FeatureValidationError as e:
            logger.error(f"Feature validation failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise RuntimeError(f"Prediction failed: {e}") from e
    
    def predict_from_request(
        self,
        request: ImpactRadiusPredictionRequest
    ) -> ImpactRadiusPredictionResponse:
        """
        Predict impact radius from a request model.
        
        Args:
            request: Validated prediction request
            
        Returns:
            Complete prediction response
        """
        return self.predict(
            disaster_type=request.disaster_type,
            latitude=request.latitude,
            longitude=request.longitude,
            features=request.features
        )
    
    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """
        Validate that coordinates are within valid ranges.
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            
        Raises:
            ValueError: If coordinates are out of valid range
        """
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(
                f"Latitude {latitude} is out of valid range [-90.0, 90.0]"
            )
        
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(
                f"Longitude {longitude} is out of valid range [-180.0, 180.0]"
            )
    
    def _enforce_bounds(self, disaster_type: DisasterType, radius: float) -> float:
        """
        Enforce realistic bounds on predicted radius.
        
        Args:
            disaster_type: Type of disaster
            radius: Predicted radius
            
        Returns:
            Radius clamped to realistic bounds
        """
        min_radius, max_radius = RADIUS_BOUNDS[disaster_type]
        
        if radius < min_radius:
            logger.warning(
                f"Radius {radius:.2f}km below minimum {min_radius}km for {disaster_type}, "
                f"clamping to minimum"
            )
            return min_radius
        
        if radius > max_radius:
            logger.warning(
                f"Radius {radius:.2f}km exceeds maximum {max_radius}km for {disaster_type}, "
                f"clamping to maximum"
            )
            return max_radius
        
        return radius
    
    def _create_geojson(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        risk_level: RiskLevel,
        disaster_type: DisasterType
    ) -> GeoJSONFeature:
        """
        Create GeoJSON representation of the threat zone.
        
        Args:
            latitude: Latitude of epicenter
            longitude: Longitude of epicenter
            radius_km: Impact radius in kilometers
            risk_level: Risk level classification
            disaster_type: Type of disaster
            
        Returns:
            GeoJSON Feature with Point geometry and properties
        """
        geometry = GeoJSONGeometry(
            type="Point",
            coordinates=[longitude, latitude]  # GeoJSON uses [lon, lat] order
        )
        
        properties = GeoJSONProperties(
            radius_km=radius_km,
            risk_level=risk_level,
            disaster_type=disaster_type.value
        )
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geometry,
            properties=properties
        )
        
        return feature
    
    def get_system_status(self) -> Dict[str, any]:
        """
        Get system status including ML model availability.
        
        Returns:
            Dictionary with system status information
        """
        return {
            "ml_models_available": self.ml_predictor.get_available_models(),
            "supported_disaster_types": [dt.value for dt in DisasterType],
            "status": "ready"
        }
