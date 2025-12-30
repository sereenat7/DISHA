"""
ML model wrapper for disaster impact radius prediction.

Provides a unified interface for loading and using trained ML models,
with fallback handling when models are unavailable.
"""

import os
import logging
from typing import Dict, Optional
import joblib
from .features import DisasterType, REQUIRED_FEATURES
from .rule_engine import RuleEngine


logger = logging.getLogger(__name__)


class MLModelPredictor:
    """
    ML model wrapper with automatic loading and fallback handling.
    
    Loads trained RandomForestRegressor models for each disaster type
    and caches them in memory. Falls back to rule-based predictions
    when models are unavailable or fail to load.
    """
    
    def __init__(self, models_dir: str = None):
        """
        Initialize the ML model predictor.
        
        Args:
            models_dir: Directory containing trained model files.
                       If None, uses the default path relative to this file.
        """
        if models_dir is None:
            # Get the directory where this file is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(current_dir, "models")
        
        self.models_dir = models_dir
        self._model_cache: Dict[DisasterType, Optional[object]] = {}
        self._rule_engine = RuleEngine()
        
        # Attempt to load all models at initialization
        self._load_all_models()
    
    def _load_all_models(self) -> None:
        """
        Attempt to load all trained models into cache.
        
        Logs warnings for any models that fail to load but continues
        execution to allow fallback to rule-based predictions.
        """
        for disaster_type in DisasterType:
            try:
                model = self._load_model(disaster_type)
                self._model_cache[disaster_type] = model
                logger.info(f"Successfully loaded ML model for {disaster_type.value}")
            except Exception as e:
                logger.warning(
                    f"Failed to load ML model for {disaster_type.value}: {e}. "
                    f"Will use rule-based fallback."
                )
                self._model_cache[disaster_type] = None
    
    def _load_model(self, disaster_type: DisasterType) -> object:
        """
        Load a trained model from disk.
        
        Args:
            disaster_type: Type of disaster
            
        Returns:
            Loaded model object
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        filename = f"{disaster_type.value}_model.joblib"
        filepath = os.path.join(self.models_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model = joblib.load(filepath)
        return model
    
    def predict(
        self, 
        disaster_type: DisasterType, 
        features: Dict[str, float],
        use_fallback: bool = True
    ) -> float:
        """
        Predict impact radius using ML model with fallback to rule engine.
        
        Args:
            disaster_type: Type of disaster
            features: Dictionary of disaster-specific features
            use_fallback: If True, fall back to rule engine when ML fails
            
        Returns:
            Predicted impact radius in kilometers
            
        Raises:
            ValueError: If disaster type is not supported
            RuntimeError: If ML prediction fails and use_fallback is False
        """
        # Check if model is available in cache
        model = self._model_cache.get(disaster_type)
        
        if model is None:
            if use_fallback:
                logger.info(
                    f"ML model not available for {disaster_type.value}, "
                    f"using rule-based fallback"
                )
                return self._rule_engine.predict(disaster_type, features)
            else:
                raise RuntimeError(
                    f"ML model not available for {disaster_type.value} "
                    f"and fallback is disabled"
                )
        
        # Attempt ML prediction
        try:
            # Convert features dict to feature vector in correct order
            feature_names = REQUIRED_FEATURES[disaster_type]
            feature_vector = [features[fname] for fname in feature_names]
            
            # Make prediction (reshape for single sample)
            import numpy as np
            X = np.array(feature_vector).reshape(1, -1)
            prediction = model.predict(X)[0]
            
            return float(prediction)
            
        except Exception as e:
            if use_fallback:
                logger.warning(
                    f"ML prediction failed for {disaster_type.value}: {e}. "
                    f"Using rule-based fallback."
                )
                return self._rule_engine.predict(disaster_type, features)
            else:
                raise RuntimeError(
                    f"ML prediction failed for {disaster_type.value}: {e}"
                ) from e
    
    def is_model_available(self, disaster_type: DisasterType) -> bool:
        """
        Check if ML model is available for a disaster type.
        
        Args:
            disaster_type: Type of disaster
            
        Returns:
            True if model is loaded and available, False otherwise
        """
        return self._model_cache.get(disaster_type) is not None
    
    def get_available_models(self) -> Dict[DisasterType, bool]:
        """
        Get availability status for all disaster type models.
        
        Returns:
            Dictionary mapping disaster types to availability status
        """
        return {
            disaster_type: self.is_model_available(disaster_type)
            for disaster_type in DisasterType
        }
    
    def reload_model(self, disaster_type: DisasterType) -> bool:
        """
        Reload a specific model from disk.
        
        Useful for updating models without restarting the application.
        
        Args:
            disaster_type: Type of disaster
            
        Returns:
            True if reload successful, False otherwise
        """
        try:
            model = self._load_model(disaster_type)
            self._model_cache[disaster_type] = model
            logger.info(f"Successfully reloaded ML model for {disaster_type.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload ML model for {disaster_type.value}: {e}")
            self._model_cache[disaster_type] = None
            return False
