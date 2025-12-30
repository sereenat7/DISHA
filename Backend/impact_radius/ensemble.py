"""
Ensemble combination logic for disaster impact radius prediction.

Combines rule-based and ML predictions using adaptive weighting,
calculates confidence scores, classifies risk levels, and generates
human-readable explanations.
"""

from typing import Dict, Tuple
from .features import DisasterType, RiskLevel, MethodUsed, RADIUS_BOUNDS


class EnsembleCombiner:
    """
    Combines rule-based and ML predictions with adaptive weighting.
    
    Implements:
    - Adaptive weighting based on data availability and model confidence
    - Confidence score calculation based on prediction agreement and data quality
    - Risk level classification (low/moderate/high/critical)
    - Human-readable explanation generation
    """
    
    def __init__(self):
        """Initialize the ensemble combiner."""
        pass
    
    def combine_predictions(
        self,
        disaster_type: DisasterType,
        rule_prediction: float,
        ml_prediction: float,
        ml_available: bool,
        features: Dict[str, float],
        feature_completeness: float = 1.0
    ) -> Tuple[float, float, float, MethodUsed]:
        """
        Combine rule-based and ML predictions using adaptive weighting.
        
        Args:
            disaster_type: Type of disaster
            rule_prediction: Prediction from rule engine (km)
            ml_prediction: Prediction from ML model (km)
            ml_available: Whether ML model is available
            features: Dictionary of disaster-specific features
            feature_completeness: Fraction of features available (0.0-1.0)
            
        Returns:
            Tuple of (final_radius, rule_weight, ml_weight, method_used)
        """
        # If ML model is not available, use rule-based only
        if not ml_available:
            return rule_prediction, 1.0, 0.0, MethodUsed.RULE_BASED
        
        # Calculate adaptive weights based on data availability
        # More complete data = higher ML weight
        # Less complete data = higher rule weight (safer)
        ml_weight = 0.3 + (feature_completeness * 0.5)  # Range: 0.3 to 0.8
        rule_weight = 1.0 - ml_weight
        
        # Calculate prediction agreement
        # If predictions diverge significantly, use more conservative (larger) radius
        avg_prediction = (rule_prediction + ml_prediction) / 2.0
        divergence = abs(rule_prediction - ml_prediction) / avg_prediction if avg_prediction > 0 else 0.0
        
        # If divergence is high (>30%), shift weight toward the more conservative prediction
        if divergence > 0.3:
            if rule_prediction > ml_prediction:
                # Rule is more conservative, increase its weight
                rule_weight = min(0.8, rule_weight + 0.2)
                ml_weight = 1.0 - rule_weight
            else:
                # ML is more conservative, increase its weight
                ml_weight = min(0.8, ml_weight + 0.2)
                rule_weight = 1.0 - ml_weight
        
        # Combine predictions using weighted average
        final_radius = (rule_weight * rule_prediction) + (ml_weight * ml_prediction)
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[disaster_type]
        final_radius = max(min_radius, min(final_radius, max_radius))
        
        return final_radius, rule_weight, ml_weight, MethodUsed.HYBRID
    
    def calculate_confidence(
        self,
        disaster_type: DisasterType,
        rule_prediction: float,
        ml_prediction: float,
        ml_available: bool,
        feature_completeness: float,
        rule_weight: float,
        ml_weight: float
    ) -> float:
        """
        Calculate confidence score based on multiple factors.
        
        Confidence factors:
        1. Prediction agreement: Higher when rule and ML predictions agree
        2. Data availability: Higher when more features are available
        3. Model availability: Higher when ML model is available
        
        Args:
            disaster_type: Type of disaster
            rule_prediction: Prediction from rule engine (km)
            ml_prediction: Prediction from ML model (km)
            ml_available: Whether ML model is available
            feature_completeness: Fraction of features available (0.0-1.0)
            rule_weight: Weight assigned to rule prediction
            ml_weight: Weight assigned to ML prediction
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence starts at 0.5
        confidence = 0.5
        
        # Factor 1: Prediction agreement (up to +0.3)
        if ml_available:
            avg_prediction = (rule_prediction + ml_prediction) / 2.0
            if avg_prediction > 0:
                divergence = abs(rule_prediction - ml_prediction) / avg_prediction
                # Lower divergence = higher confidence
                agreement_score = max(0.0, 1.0 - divergence)
                confidence += agreement_score * 0.3
        else:
            # No ML model, moderate confidence boost for rule-only
            confidence += 0.1
        
        # Factor 2: Data availability (up to +0.2)
        confidence += feature_completeness * 0.2
        
        # Factor 3: Model availability (up to +0.1)
        if ml_available:
            confidence += 0.1
        
        # Ensure confidence is in valid range [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def classify_risk_level(
        self,
        disaster_type: DisasterType,
        radius_km: float,
        features: Dict[str, float]
    ) -> RiskLevel:
        """
        Classify risk level based on radius and disaster-specific factors.
        
        Risk levels:
        - LOW: Small radius, minimal threat
        - MODERATE: Medium radius, localized threat
        - HIGH: Large radius, significant threat
        - CRITICAL: Very large radius or extreme disaster parameters
        
        Args:
            disaster_type: Type of disaster
            radius_km: Predicted impact radius
            features: Dictionary of disaster-specific features
            
        Returns:
            Risk level classification
        """
        # Get bounds for this disaster type
        min_radius, max_radius = RADIUS_BOUNDS[disaster_type]
        radius_range = max_radius - min_radius
        
        # Calculate normalized radius (0.0 to 1.0)
        normalized_radius = (radius_km - min_radius) / radius_range if radius_range > 0 else 0.5
        
        # Base classification on normalized radius
        if normalized_radius < 0.25:
            base_level = RiskLevel.LOW
        elif normalized_radius < 0.5:
            base_level = RiskLevel.MODERATE
        elif normalized_radius < 0.75:
            base_level = RiskLevel.HIGH
        else:
            base_level = RiskLevel.CRITICAL
        
        # Apply disaster-specific adjustments
        if disaster_type == DisasterType.EARTHQUAKE:
            magnitude = features.get("magnitude", 0.0)
            if magnitude >= 7.0:
                return RiskLevel.CRITICAL
            elif magnitude >= 6.0 and base_level == RiskLevel.HIGH:
                return RiskLevel.CRITICAL
        
        elif disaster_type == DisasterType.CYCLONE:
            wind_speed = features.get("wind_speed", 0.0)
            if wind_speed >= 252.0:  # Category 5
                return RiskLevel.CRITICAL
            elif wind_speed >= 209.0 and base_level == RiskLevel.HIGH:  # Category 4
                return RiskLevel.CRITICAL
        
        elif disaster_type == DisasterType.FIRE:
            fire_intensity = features.get("fire_intensity", 0.0)
            wind_speed = features.get("wind_speed", 0.0)
            humidity = features.get("humidity", 100.0)
            # Extreme fire conditions
            if fire_intensity >= 80.0 and wind_speed >= 60.0 and humidity <= 20.0:
                return RiskLevel.CRITICAL
        
        elif disaster_type == DisasterType.FLOOD:
            rainfall_intensity = features.get("rainfall_intensity", 0.0)
            duration = features.get("duration", 0.0)
            # Extreme rainfall
            if rainfall_intensity >= 100.0 and duration >= 12.0:
                return RiskLevel.CRITICAL
        
        elif disaster_type == DisasterType.GAS_LEAK:
            leak_severity = features.get("leak_severity", 0.0)
            if leak_severity >= 9.0:
                return RiskLevel.CRITICAL
        
        return base_level
    
    def generate_explanation(
        self,
        disaster_type: DisasterType,
        radius_km: float,
        confidence_score: float,
        risk_level: RiskLevel,
        method_used: MethodUsed,
        rule_weight: float,
        ml_weight: float,
        features: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation of the prediction.
        
        Args:
            disaster_type: Type of disaster
            radius_km: Predicted impact radius
            confidence_score: Confidence score (0.0-1.0)
            risk_level: Risk level classification
            method_used: Prediction method used
            rule_weight: Weight assigned to rule prediction
            ml_weight: Weight assigned to ML prediction
            features: Dictionary of disaster-specific features
            
        Returns:
            Human-readable explanation string
        """
        explanation_parts = []
        
        # Start with disaster type and key parameters
        if disaster_type == DisasterType.EARTHQUAKE:
            magnitude = features.get("magnitude", 0.0)
            depth = features.get("depth", 0.0)
            explanation_parts.append(
                f"Earthquake magnitude {magnitude:.1f} at depth {depth:.1f}km."
            )
        
        elif disaster_type == DisasterType.FLOOD:
            rainfall = features.get("rainfall_intensity", 0.0)
            duration = features.get("duration", 0.0)
            explanation_parts.append(
                f"Flood with rainfall intensity {rainfall:.1f}mm/hr over {duration:.1f} hours."
            )
        
        elif disaster_type == DisasterType.FIRE:
            intensity = features.get("fire_intensity", 0.0)
            wind = features.get("wind_speed", 0.0)
            explanation_parts.append(
                f"Fire with intensity {intensity:.1f}/100 and wind speed {wind:.1f}km/h."
            )
        
        elif disaster_type == DisasterType.CYCLONE:
            wind = features.get("wind_speed", 0.0)
            pressure = features.get("atmospheric_pressure", 0.0)
            explanation_parts.append(
                f"Cyclone with wind speed {wind:.1f}km/h and pressure {pressure:.1f}hPa."
            )
        
        elif disaster_type == DisasterType.GAS_LEAK:
            severity = features.get("leak_severity", 0.0)
            wind = features.get("wind_speed", 0.0)
            explanation_parts.append(
                f"Gas leak severity {severity:.1f}/10 with wind speed {wind:.1f}km/h."
            )
        
        # Add prediction method information
        if method_used == MethodUsed.RULE_BASED:
            explanation_parts.append(
                "Prediction based on physics-based heuristics (rule engine)."
            )
        elif method_used == MethodUsed.ML_BASED:
            explanation_parts.append(
                "Prediction based on machine learning model."
            )
        elif method_used == MethodUsed.HYBRID:
            explanation_parts.append(
                f"Hybrid prediction combining rule-based ({rule_weight*100:.0f}%) "
                f"and ML model ({ml_weight*100:.0f}%)."
            )
        
        # Add confidence information
        confidence_pct = confidence_score * 100
        if confidence_score >= 0.8:
            confidence_desc = "high"
        elif confidence_score >= 0.6:
            confidence_desc = "moderate"
        else:
            confidence_desc = "low"
        
        explanation_parts.append(
            f"Confidence: {confidence_desc} ({confidence_pct:.0f}%)."
        )
        
        # Add risk level context
        explanation_parts.append(
            f"Risk level: {risk_level.value}. "
            f"Predicted impact radius: {radius_km:.1f}km."
        )
        
        return " ".join(explanation_parts)
