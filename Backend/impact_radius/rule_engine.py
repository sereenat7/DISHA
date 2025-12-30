"""
Rule-based prediction engine for disaster impact radius.

Implements physics-based heuristics as a safety baseline for each disaster type.
"""

import math
from typing import Dict
from .features import DisasterType, RADIUS_BOUNDS


class RuleEngine:
    """
    Rule-based prediction engine using physics-based heuristics.
    
    Each disaster type has a scientifically-grounded formula that serves
    as a conservative baseline prediction when ML models are unavailable
    or have low confidence.
    """
    
    def predict(self, disaster_type: DisasterType, features: Dict[str, float]) -> float:
        """
        Predict impact radius using rule-based heuristics.
        
        Args:
            disaster_type: Type of disaster
            features: Dictionary of disaster-specific features
            
        Returns:
            Predicted impact radius in kilometers
            
        Raises:
            ValueError: If disaster type is not supported
        """
        if disaster_type == DisasterType.FLOOD:
            return self._predict_flood(features)
        elif disaster_type == DisasterType.EARTHQUAKE:
            return self._predict_earthquake(features)
        elif disaster_type == DisasterType.FIRE:
            return self._predict_fire(features)
        elif disaster_type == DisasterType.CYCLONE:
            return self._predict_cyclone(features)
        elif disaster_type == DisasterType.GAS_LEAK:
            return self._predict_gas_leak(features)
        else:
            raise ValueError(f"Unsupported disaster type: {disaster_type}")
    
    def _predict_flood(self, features: Dict[str, float]) -> float:
        """
        Predict flood impact radius.
        
        Formula based on rainfall intensity, duration, elevation, and river proximity.
        Higher rainfall and longer duration increase radius.
        Lower elevation and closer river proximity increase radius.
        
        Args:
            features: Must contain rainfall_intensity, duration, elevation, river_proximity
            
        Returns:
            Impact radius in kilometers
        """
        rainfall_intensity = features["rainfall_intensity"]  # mm/hour
        duration = features["duration"]  # hours
        elevation = features["elevation"]  # meters
        river_proximity = features["river_proximity"]  # km
        
        # Base radius from rainfall accumulation
        total_rainfall = rainfall_intensity * duration  # mm
        base_radius = math.sqrt(total_rainfall) * 0.1  # km
        
        # Elevation factor: lower elevation = larger radius
        # Normalize elevation to [-500, 9000] -> [2.0, 0.5]
        elevation_factor = max(0.5, 2.0 - (elevation + 500) / 9500 * 1.5)
        
        # River proximity factor: closer river = larger radius
        # Normalize to [0, 100] -> [2.0, 1.0]
        river_factor = max(1.0, 2.0 - river_proximity / 100.0)
        
        radius = base_radius * elevation_factor * river_factor
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[DisasterType.FLOOD]
        return max(min_radius, min(radius, max_radius))
    
    def _predict_earthquake(self, features: Dict[str, float]) -> float:
        """
        Predict earthquake impact radius.
        
        Formula based on magnitude, depth, and soil type.
        Uses exponential relationship with magnitude (Richter scale).
        Shallower earthquakes and softer soil increase radius.
        
        Args:
            features: Must contain magnitude, depth, soil_type
            
        Returns:
            Impact radius in kilometers
        """
        magnitude = features["magnitude"]  # Richter scale
        depth = features["depth"]  # km
        soil_type = features["soil_type"]  # 1-5 scale
        
        # Exponential relationship with magnitude
        # Each magnitude increase roughly doubles the radius
        base_radius = 2.0 ** (magnitude - 3.0)  # km
        
        # Depth factor: shallower = larger radius
        # Normalize depth [0, 700] -> [2.0, 0.5]
        depth_factor = max(0.5, 2.0 - depth / 700.0 * 1.5)
        
        # Soil type factor: softer soil = larger radius
        # soil_type: 1=rock (0.8x), 5=fill (1.5x)
        soil_factor = 0.8 + (soil_type - 1) * 0.175
        
        radius = base_radius * depth_factor * soil_factor
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[DisasterType.EARTHQUAKE]
        return max(min_radius, min(radius, max_radius))
    
    def _predict_fire(self, features: Dict[str, float]) -> float:
        """
        Predict fire impact radius.
        
        Formula based on fire intensity, wind speed, humidity, and temperature.
        Wind speed is the dominant factor for fire spread.
        Low humidity and high temperature increase radius.
        
        Args:
            features: Must contain fire_intensity, wind_speed, wind_direction, 
                     humidity, temperature
            
        Returns:
            Impact radius in kilometers
        """
        fire_intensity = features["fire_intensity"]  # 0-100 scale
        wind_speed = features["wind_speed"]  # km/h
        humidity = features["humidity"]  # percentage
        temperature = features["temperature"]  # Celsius
        
        # Base radius from fire intensity
        base_radius = fire_intensity * 0.15  # km
        
        # Wind factor: dominant factor for fire spread
        # Normalize wind_speed [0, 200] -> [1.0, 3.0]
        wind_factor = 1.0 + (wind_speed / 200.0) * 2.0
        
        # Humidity factor: lower humidity = larger radius
        # Normalize humidity [0, 100] -> [1.5, 0.7]
        humidity_factor = max(0.7, 1.5 - humidity / 100.0 * 0.8)
        
        # Temperature factor: higher temperature = larger radius
        # Normalize temperature [-50, 60] -> [0.8, 1.3]
        temp_normalized = (temperature + 50) / 110.0  # [0, 1]
        temperature_factor = 0.8 + temp_normalized * 0.5
        
        radius = base_radius * wind_factor * humidity_factor * temperature_factor
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[DisasterType.FIRE]
        return max(min_radius, min(radius, max_radius))
    
    def _predict_cyclone(self, features: Dict[str, float]) -> float:
        """
        Predict cyclone impact radius.
        
        Formula based on wind speed, atmospheric pressure, movement speed,
        and coastal proximity. Wind speed is the primary factor.
        
        Args:
            features: Must contain wind_speed, atmospheric_pressure, 
                     movement_speed, coastal_proximity
            
        Returns:
            Impact radius in kilometers
        """
        wind_speed = features["wind_speed"]  # km/h
        atmospheric_pressure = features["atmospheric_pressure"]  # hPa
        movement_speed = features["movement_speed"]  # km/h
        coastal_proximity = features["coastal_proximity"]  # km
        
        # Base radius from wind speed (Saffir-Simpson scale relationship)
        # Category 1: 119-153 km/h, Category 5: >252 km/h
        base_radius = wind_speed * 0.5  # km
        
        # Pressure factor: lower pressure = larger radius
        # Normalize pressure [870, 1050] -> [1.5, 0.8]
        pressure_normalized = (atmospheric_pressure - 870) / 180.0
        pressure_factor = max(0.8, 1.5 - pressure_normalized * 0.7)
        
        # Movement speed factor: slower = larger radius (more time to intensify)
        # Normalize movement_speed [0, 100] -> [1.3, 0.9]
        movement_factor = max(0.9, 1.3 - movement_speed / 100.0 * 0.4)
        
        # Coastal proximity factor: closer to coast = larger radius
        # Normalize coastal_proximity [0, 1000] -> [1.2, 1.0]
        coastal_factor = 1.0 + (1.0 - min(coastal_proximity, 1000) / 1000.0) * 0.2
        
        radius = base_radius * pressure_factor * movement_factor * coastal_factor
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[DisasterType.CYCLONE]
        return max(min_radius, min(radius, max_radius))
    
    def _predict_gas_leak(self, features: Dict[str, float]) -> float:
        """
        Predict gas leak impact radius.
        
        Formula based on wind speed, atmospheric stability, and leak severity.
        Uses Gaussian plume dispersion model principles.
        
        Args:
            features: Must contain wind_speed, atmospheric_stability, leak_severity
            
        Returns:
            Impact radius in kilometers
        """
        wind_speed = features["wind_speed"]  # km/h
        atmospheric_stability = features["atmospheric_stability"]  # 1-6 (Pasquill)
        leak_severity = features["leak_severity"]  # 1-10 scale
        
        # Base radius from leak severity
        base_radius = leak_severity * 0.3  # km
        
        # Wind factor: higher wind = larger dispersion
        # Normalize wind_speed [0, 200] -> [0.8, 1.5]
        wind_factor = 0.8 + (wind_speed / 200.0) * 0.7
        
        # Stability factor: unstable atmosphere = larger dispersion
        # Pasquill classes: 1=A (very unstable), 6=F (very stable)
        # Normalize [1, 6] -> [1.5, 0.7]
        stability_factor = max(0.7, 1.5 - (atmospheric_stability - 1) / 5.0 * 0.8)
        
        radius = base_radius * wind_factor * stability_factor
        
        # Enforce realistic bounds
        min_radius, max_radius = RADIUS_BOUNDS[DisasterType.GAS_LEAK]
        return max(min_radius, min(radius, max_radius))
