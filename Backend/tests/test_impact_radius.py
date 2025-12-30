"""
Property-based tests for disaster impact radius prediction system.

Feature: disaster-impact-radius
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from impact_radius.features import (
    DisasterType,
    REQUIRED_FEATURES,
    FEATURE_BOUNDS,
    RADIUS_BOUNDS,
    validate_features,
    FeatureValidationError,
    ImpactRadiusPredictionRequest,
)
from impact_radius.rule_engine import RuleEngine


# Strategies for generating test data
disaster_types = st.sampled_from(list(DisasterType))


def valid_feature_value(feature_name: str) -> st.SearchStrategy:
    """Generate valid values for a given feature."""
    if feature_name in FEATURE_BOUNDS:
        min_val, max_val = FEATURE_BOUNDS[feature_name]
        return st.floats(min_value=min_val, max_value=max_val, allow_nan=False, allow_infinity=False)
    return st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)


def invalid_feature_value(feature_name: str) -> st.SearchStrategy:
    """Generate invalid (out-of-range) values for a given feature."""
    if feature_name in FEATURE_BOUNDS:
        min_val, max_val = FEATURE_BOUNDS[feature_name]
        return st.one_of(
            st.floats(min_value=-1e6, max_value=min_val - 0.01, allow_nan=False, allow_infinity=False),
            st.floats(min_value=max_val + 0.01, max_value=1e6, allow_nan=False, allow_infinity=False)
        )
    return st.floats(min_value=-1000.0, max_value=-0.01, allow_nan=False, allow_infinity=False)


@st.composite
def complete_valid_features(draw, disaster_type: DisasterType):
    """Generate a complete set of valid features for a disaster type."""
    required = REQUIRED_FEATURES[disaster_type]
    features = {}
    for feature_name in required:
        features[feature_name] = draw(valid_feature_value(feature_name))
    return features


@st.composite
def incomplete_features(draw, disaster_type: DisasterType):
    """Generate an incomplete set of features (missing at least one required feature)."""
    required = REQUIRED_FEATURES[disaster_type]
    if len(required) == 0:
        return {}
    
    # Remove at least one required feature
    num_to_include = draw(st.integers(min_value=0, max_value=len(required) - 1))
    features_to_include = draw(st.lists(
        st.sampled_from(required),
        min_size=num_to_include,
        max_size=num_to_include,
        unique=True
    ))
    
    features = {}
    for feature_name in features_to_include:
        features[feature_name] = draw(valid_feature_value(feature_name))
    
    return features


@st.composite
def features_with_invalid_range(draw, disaster_type: DisasterType):
    """Generate features where at least one value is out of valid range."""
    required = REQUIRED_FEATURES[disaster_type]
    features = {}
    
    # Generate valid values for all features
    for feature_name in required:
        features[feature_name] = draw(valid_feature_value(feature_name))
    
    # Pick one feature to make invalid
    invalid_feature = draw(st.sampled_from(required))
    features[invalid_feature] = draw(invalid_feature_value(invalid_feature))
    
    return features


# Property 4: Feature Validation Completeness
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 10.1
@settings(max_examples=100)
@given(disaster_type=disaster_types, features=st.data())
def test_property_4_missing_required_features_raises_error(disaster_type, features):
    """
    Feature: disaster-impact-radius, Property 4: Feature Validation Completeness
    
    For any disaster type and incomplete feature set (missing at least one required feature),
    validation should raise FeatureValidationError.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 10.1
    """
    incomplete_feature_dict = features.draw(incomplete_features(disaster_type))
    
    # Verify that at least one required feature is missing
    required = REQUIRED_FEATURES[disaster_type]
    missing = [f for f in required if f not in incomplete_feature_dict]
    
    if missing:  # Only test if features are actually incomplete
        with pytest.raises(FeatureValidationError) as exc_info:
            validate_features(disaster_type, incomplete_feature_dict)
        
        # Verify error message mentions missing features
        assert "Missing required features" in str(exc_info.value)


# Property 5: Feature Range Validation
# Validates: Requirements 10.2
@settings(max_examples=100)
@given(disaster_type=disaster_types, features=st.data())
def test_property_5_out_of_range_features_raises_error(disaster_type, features):
    """
    Feature: disaster-impact-radius, Property 5: Feature Range Validation
    
    For any disaster type and feature set with at least one out-of-range value,
    validation should raise FeatureValidationError.
    
    Validates: Requirements 10.2
    """
    invalid_feature_dict = features.draw(features_with_invalid_range(disaster_type))
    
    with pytest.raises(FeatureValidationError) as exc_info:
        validate_features(disaster_type, invalid_feature_dict)
    
    # Verify error message mentions out of range
    assert "out of valid range" in str(exc_info.value)


# Additional test: Valid features should pass validation
@settings(max_examples=100)
@given(disaster_type=disaster_types, features=st.data())
def test_valid_features_pass_validation(disaster_type, features):
    """
    Sanity check: Complete and valid feature sets should pass validation.
    """
    valid_feature_dict = features.draw(complete_valid_features(disaster_type))
    
    # Should not raise any exception
    validate_features(disaster_type, valid_feature_dict)


# Additional test: ImpactRadiusPredictionRequest model validation
@settings(max_examples=100)
@given(
    disaster_type=disaster_types,
    latitude=st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False),
    longitude=st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    features=st.data()
)
def test_request_model_with_valid_features(disaster_type, latitude, longitude, features):
    """
    Test that ImpactRadiusPredictionRequest accepts valid inputs.
    """
    valid_feature_dict = features.draw(complete_valid_features(disaster_type))
    
    # Should create successfully
    request = ImpactRadiusPredictionRequest(
        disaster_type=disaster_type,
        latitude=latitude,
        longitude=longitude,
        features=valid_feature_dict
    )
    
    assert request.disaster_type == disaster_type
    assert request.latitude == latitude
    assert request.longitude == longitude
    assert request.features == valid_feature_dict


# ============================================================================
# Unit Tests for Rule Engine Formulas
# ============================================================================

class TestRuleEngineFormulas:
    """Unit tests for rule-based prediction formulas."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = RuleEngine()
    
    # Flood tests
    def test_flood_basic_prediction(self):
        """Test flood prediction with typical values."""
        features = {
            "rainfall_intensity": 50.0,  # mm/hour
            "duration": 10.0,  # hours
            "elevation": 100.0,  # meters
            "river_proximity": 5.0  # km
        }
        radius = self.engine.predict(DisasterType.FLOOD, features)
        
        # Should return a positive value within bounds
        min_r, max_r = RADIUS_BOUNDS[DisasterType.FLOOD]
        assert min_r <= radius <= max_r
        assert radius > 0
    
    def test_flood_high_rainfall(self):
        """Test flood with extreme rainfall."""
        features = {
            "rainfall_intensity": 200.0,
            "duration": 24.0,
            "elevation": 50.0,
            "river_proximity": 1.0
        }
        radius = self.engine.predict(DisasterType.FLOOD, features)
        
        # High rainfall should produce larger radius
        assert radius > 10.0
    
    def test_flood_boundary_conditions(self):
        """Test flood with minimum and maximum feature values."""
        # Minimum values
        features_min = {
            "rainfall_intensity": 0.0,
            "duration": 0.0,
            "elevation": -500.0,
            "river_proximity": 0.0
        }
        radius_min = self.engine.predict(DisasterType.FLOOD, features_min)
        min_r, max_r = RADIUS_BOUNDS[DisasterType.FLOOD]
        assert radius_min == min_r  # Should hit minimum bound
        
        # Maximum values
        features_max = {
            "rainfall_intensity": 500.0,
            "duration": 168.0,
            "elevation": 9000.0,
            "river_proximity": 100.0
        }
        radius_max = self.engine.predict(DisasterType.FLOOD, features_max)
        assert radius_max <= max_r  # Should not exceed maximum bound
    
    # Earthquake tests
    def test_earthquake_basic_prediction(self):
        """Test earthquake prediction with typical values."""
        features = {
            "magnitude": 6.5,
            "depth": 10.0,
            "soil_type": 3.0
        }
        radius = self.engine.predict(DisasterType.EARTHQUAKE, features)
        
        min_r, max_r = RADIUS_BOUNDS[DisasterType.EARTHQUAKE]
        assert min_r <= radius <= max_r
        assert radius > 0
    
    def test_earthquake_magnitude_scaling(self):
        """Test that higher magnitude produces larger radius."""
        features_low = {
            "magnitude": 4.0,
            "depth": 10.0,
            "soil_type": 3.0
        }
        features_high = {
            "magnitude": 7.0,
            "depth": 10.0,
            "soil_type": 3.0
        }
        
        radius_low = self.engine.predict(DisasterType.EARTHQUAKE, features_low)
        radius_high = self.engine.predict(DisasterType.EARTHQUAKE, features_high)
        
        assert radius_high > radius_low
    
    def test_earthquake_depth_effect(self):
        """Test that shallower earthquakes produce larger radius."""
        features_shallow = {
            "magnitude": 6.0,
            "depth": 5.0,
            "soil_type": 3.0
        }
        features_deep = {
            "magnitude": 6.0,
            "depth": 100.0,
            "soil_type": 3.0
        }
        
        radius_shallow = self.engine.predict(DisasterType.EARTHQUAKE, features_shallow)
        radius_deep = self.engine.predict(DisasterType.EARTHQUAKE, features_deep)
        
        assert radius_shallow > radius_deep
    
    # Fire tests
    def test_fire_basic_prediction(self):
        """Test fire prediction with typical values."""
        features = {
            "fire_intensity": 60.0,
            "wind_speed": 30.0,
            "wind_direction": 180.0,
            "humidity": 40.0,
            "temperature": 30.0
        }
        radius = self.engine.predict(DisasterType.FIRE, features)
        
        min_r, max_r = RADIUS_BOUNDS[DisasterType.FIRE]
        assert min_r <= radius <= max_r
        assert radius > 0
    
    def test_fire_wind_effect(self):
        """Test that higher wind speed increases fire radius."""
        features_low_wind = {
            "fire_intensity": 50.0,
            "wind_speed": 10.0,
            "wind_direction": 0.0,
            "humidity": 50.0,
            "temperature": 25.0
        }
        features_high_wind = {
            "fire_intensity": 50.0,
            "wind_speed": 80.0,
            "wind_direction": 0.0,
            "humidity": 50.0,
            "temperature": 25.0
        }
        
        radius_low = self.engine.predict(DisasterType.FIRE, features_low_wind)
        radius_high = self.engine.predict(DisasterType.FIRE, features_high_wind)
        
        assert radius_high > radius_low
    
    def test_fire_extreme_conditions(self):
        """Test fire with extreme weather conditions."""
        features = {
            "fire_intensity": 90.0,
            "wind_speed": 100.0,
            "wind_direction": 90.0,
            "humidity": 10.0,  # Very dry
            "temperature": 45.0  # Very hot
        }
        radius = self.engine.predict(DisasterType.FIRE, features)
        
        # Extreme conditions should produce large radius
        assert radius > 15.0
    
    # Cyclone tests
    def test_cyclone_basic_prediction(self):
        """Test cyclone prediction with typical values."""
        features = {
            "wind_speed": 150.0,
            "atmospheric_pressure": 950.0,
            "movement_speed": 20.0,
            "coastal_proximity": 50.0
        }
        radius = self.engine.predict(DisasterType.CYCLONE, features)
        
        min_r, max_r = RADIUS_BOUNDS[DisasterType.CYCLONE]
        assert min_r <= radius <= max_r
        assert radius > 0
    
    def test_cyclone_category_5(self):
        """Test cyclone with Category 5 hurricane conditions."""
        features = {
            "wind_speed": 280.0,  # Category 5
            "atmospheric_pressure": 900.0,  # Very low
            "movement_speed": 15.0,
            "coastal_proximity": 10.0
        }
        radius = self.engine.predict(DisasterType.CYCLONE, features)
        
        # Category 5 should produce very large radius
        assert radius > 100.0
    
    # Gas leak tests
    def test_gas_leak_basic_prediction(self):
        """Test gas leak prediction with typical values."""
        features = {
            "wind_speed": 20.0,
            "atmospheric_stability": 3.0,
            "leak_severity": 5.0
        }
        radius = self.engine.predict(DisasterType.GAS_LEAK, features)
        
        min_r, max_r = RADIUS_BOUNDS[DisasterType.GAS_LEAK]
        assert min_r <= radius <= max_r
        assert radius > 0
    
    def test_gas_leak_severe(self):
        """Test gas leak with severe conditions."""
        features = {
            "wind_speed": 50.0,
            "atmospheric_stability": 1.0,  # Very unstable
            "leak_severity": 10.0  # Maximum severity
        }
        radius = self.engine.predict(DisasterType.GAS_LEAK, features)
        
        # Severe leak should produce larger radius
        assert radius > 2.0
    
    def test_gas_leak_stable_atmosphere(self):
        """Test that stable atmosphere reduces gas leak radius."""
        features_unstable = {
            "wind_speed": 30.0,
            "atmospheric_stability": 1.0,  # Unstable
            "leak_severity": 5.0
        }
        features_stable = {
            "wind_speed": 30.0,
            "atmospheric_stability": 6.0,  # Stable
            "leak_severity": 5.0
        }
        
        radius_unstable = self.engine.predict(DisasterType.GAS_LEAK, features_unstable)
        radius_stable = self.engine.predict(DisasterType.GAS_LEAK, features_stable)
        
        assert radius_unstable > radius_stable
    
    # Edge case tests
    def test_zero_values(self):
        """Test handling of zero values in features."""
        # Flood with zero rainfall
        features = {
            "rainfall_intensity": 0.0,
            "duration": 0.0,
            "elevation": 0.0,
            "river_proximity": 0.0
        }
        radius = self.engine.predict(DisasterType.FLOOD, features)
        
        # Should still return minimum valid radius
        min_r, _ = RADIUS_BOUNDS[DisasterType.FLOOD]
        assert radius == min_r
    
    def test_all_disaster_types_return_positive_radius(self):
        """Test that all disaster types return positive radius."""
        test_cases = {
            DisasterType.FLOOD: {
                "rainfall_intensity": 50.0,
                "duration": 10.0,
                "elevation": 100.0,
                "river_proximity": 5.0
            },
            DisasterType.EARTHQUAKE: {
                "magnitude": 6.0,
                "depth": 10.0,
                "soil_type": 3.0
            },
            DisasterType.FIRE: {
                "fire_intensity": 50.0,
                "wind_speed": 30.0,
                "wind_direction": 180.0,
                "humidity": 40.0,
                "temperature": 25.0
            },
            DisasterType.CYCLONE: {
                "wind_speed": 150.0,
                "atmospheric_pressure": 950.0,
                "movement_speed": 20.0,
                "coastal_proximity": 50.0
            },
            DisasterType.GAS_LEAK: {
                "wind_speed": 20.0,
                "atmospheric_stability": 3.0,
                "leak_severity": 5.0
            }
        }
        
        for disaster_type, features in test_cases.items():
            radius = self.engine.predict(disaster_type, features)
            assert radius > 0, f"{disaster_type} returned non-positive radius"



# ============================================================================
# Property Tests for Rule Engine
# ============================================================================

# Property 1: Disaster Type Support Completeness
# Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
@settings(max_examples=100)
@given(disaster_type=disaster_types, features=st.data())
def test_property_1_all_disaster_types_return_valid_predictions(disaster_type, features):
    """
    Feature: disaster-impact-radius, Property 1: Disaster Type Support Completeness
    
    For any supported disaster type with valid features, the rule engine should
    return a valid prediction (positive radius within bounds).
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
    """
    engine = RuleEngine()
    valid_feature_dict = features.draw(complete_valid_features(disaster_type))
    
    # Should return a valid radius
    radius = engine.predict(disaster_type, valid_feature_dict)
    
    # Verify radius is positive
    assert radius > 0, f"Radius should be positive, got {radius}"
    
    # Verify radius is within realistic bounds
    min_radius, max_radius = RADIUS_BOUNDS[disaster_type]
    assert min_radius <= radius <= max_radius, \
        f"Radius {radius} outside bounds [{min_radius}, {max_radius}] for {disaster_type}"



# Property 2: Unsupported Disaster Type Rejection
# Validates: Requirements 1.6
@settings(max_examples=100)
@given(
    invalid_type=st.text(min_size=1, max_size=50).filter(
        lambda x: x not in [dt.value for dt in DisasterType]
    ),
    features=st.dictionaries(
        keys=st.text(min_size=1, max_size=30),
        values=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=10
    )
)
def test_property_2_unsupported_disaster_types_raise_error(invalid_type, features):
    """
    Feature: disaster-impact-radius, Property 2: Unsupported Disaster Type Rejection
    
    For any invalid disaster type (not in the supported list), the rule engine
    should raise a descriptive ValueError.
    
    Validates: Requirements 1.6
    """
    engine = RuleEngine()
    
    # Attempt to predict with invalid disaster type
    # We need to bypass the DisasterType enum, so we'll call the internal methods
    # or create a mock disaster type
    with pytest.raises(ValueError) as exc_info:
        # Create a mock disaster type that's not in the enum
        class MockDisasterType:
            def __init__(self, value):
                self.value = value
            def __eq__(self, other):
                return False  # Never equals any real DisasterType
            def __str__(self):
                return self.value
        
        mock_type = MockDisasterType(invalid_type)
        engine.predict(mock_type, features)
    
    # Verify error message is descriptive
    error_message = str(exc_info.value)
    assert "Unsupported disaster type" in error_message or "not supported" in error_message.lower()


# ============================================================================
# Unit Tests for Training Pipeline
# ============================================================================

import os
import tempfile
import shutil


class TestSyntheticDataGeneration:
    """Unit tests for synthetic data generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from impact_radius.training.synthetic_data import SyntheticDataGenerator
        self.generator = SyntheticDataGenerator(seed=42)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_random_features_returns_complete_set(self):
        """Test that random feature generation includes all required features."""
        for disaster_type in DisasterType:
            features = self.generator.generate_random_features(disaster_type)
            
            # Verify all required features are present
            required = REQUIRED_FEATURES[disaster_type]
            assert set(features.keys()) == set(required), \
                f"Generated features {features.keys()} don't match required {required}"
            
            # Verify all values are within bounds
            for feature_name, value in features.items():
                min_val, max_val = FEATURE_BOUNDS[feature_name]
                assert min_val <= value <= max_val, \
                    f"Feature {feature_name}={value} outside bounds [{min_val}, {max_val}]"
    
    def test_generate_samples_produces_valid_count(self):
        """Test that sample generation produces the requested number of samples."""
        num_samples = 50
        samples = self.generator.generate_samples(DisasterType.FLOOD, num_samples)
        
        assert len(samples) == num_samples, \
            f"Expected {num_samples} samples, got {len(samples)}"
    
    def test_generate_samples_includes_target_radius(self):
        """Test that generated samples include target radius_km field."""
        samples = self.generator.generate_samples(DisasterType.EARTHQUAKE, 10)
        
        for sample in samples:
            assert 'radius_km' in sample, "Sample missing radius_km field"
            assert sample['radius_km'] > 0, "Radius should be positive"
    
    def test_generate_samples_adds_noise_to_predictions(self):
        """Test that generated samples have variability (noise added)."""
        # Generate samples with same seed
        samples = self.generator.generate_samples(DisasterType.FIRE, 100)
        
        # Extract radius values
        radii = [s['radius_km'] for s in samples]
        
        # Verify there's variability (not all the same)
        unique_radii = set(radii)
        assert len(unique_radii) > 10, \
            "Expected variability in generated radii, but got too few unique values"
    
    def test_save_to_csv_creates_file(self):
        """Test that CSV saving creates a file with correct structure."""
        samples = self.generator.generate_samples(DisasterType.CYCLONE, 20)
        filepath = self.generator.save_to_csv(samples, DisasterType.CYCLONE, self.temp_dir)
        
        # Verify file exists
        assert os.path.exists(filepath), f"CSV file not created at {filepath}"
        
        # Verify file has correct name
        assert "cyclone_training_data.csv" in filepath
        
        # Verify file has content
        with open(filepath, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 20, "CSV should have header + data rows"
    
    def test_generate_all_datasets_creates_all_files(self):
        """Test that generating all datasets creates files for each disaster type."""
        file_paths = self.generator.generate_all_datasets(
            num_samples_per_type=10,
            output_dir=self.temp_dir
        )
        
        # Verify we have files for all disaster types
        assert len(file_paths) == len(DisasterType), \
            f"Expected {len(DisasterType)} files, got {len(file_paths)}"
        
        # Verify all files exist
        for disaster_type, filepath in file_paths.items():
            assert os.path.exists(filepath), \
                f"File for {disaster_type} not found at {filepath}"


class TestMLModelPredictor:
    """Unit tests for ML model predictor with fallback."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from impact_radius.ml_models import MLModelPredictor
        
        # Create predictor with non-existent models directory
        # This ensures models won't load and fallback will be used
        self.predictor_no_models = MLModelPredictor(models_dir="/nonexistent/path")
    
    def test_predictor_with_missing_models_uses_fallback(self):
        """Test that predictor falls back to rule engine when models are missing."""
        # All models should be unavailable
        available = self.predictor_no_models.get_available_models()
        assert all(not status for status in available.values()), \
            "Expected all models to be unavailable"
        
        # Should still be able to make predictions using fallback
        features = {
            "magnitude": 6.0,
            "depth": 10.0,
            "soil_type": 3.0
        }
        radius = self.predictor_no_models.predict(DisasterType.EARTHQUAKE, features)
        
        # Should return a valid radius from rule engine
        assert radius > 0
        min_r, max_r = RADIUS_BOUNDS[DisasterType.EARTHQUAKE]
        assert min_r <= radius <= max_r
    
    def test_is_model_available_returns_false_for_missing_models(self):
        """Test that is_model_available correctly reports missing models."""
        for disaster_type in DisasterType:
            assert not self.predictor_no_models.is_model_available(disaster_type), \
                f"Model for {disaster_type} should not be available"
    
    def test_predict_without_fallback_raises_error(self):
        """Test that prediction fails when fallback is disabled and model is missing."""
        features = {
            "rainfall_intensity": 50.0,
            "duration": 10.0,
            "elevation": 100.0,
            "river_proximity": 5.0
        }
        
        with pytest.raises(RuntimeError) as exc_info:
            self.predictor_no_models.predict(
                DisasterType.FLOOD, 
                features, 
                use_fallback=False
            )
        
        assert "not available" in str(exc_info.value).lower()


class TestModelTraining:
    """Unit tests for model training pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from impact_radius.training.synthetic_data import SyntheticDataGenerator
        from impact_radius.training.train_models import ModelTrainer
        
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, "data")
        self.models_dir = os.path.join(self.temp_dir, "models")
        
        # Generate small training datasets
        generator = SyntheticDataGenerator(seed=42)
        generator.generate_all_datasets(
            num_samples_per_type=100,
            output_dir=self.data_dir
        )
        
        self.trainer = ModelTrainer(n_estimators=10, max_depth=5, random_state=42)
    
    def teardown_method(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_training_data_returns_correct_shapes(self):
        """Test that training data loading returns correct array shapes."""
        X, y, feature_names = self.trainer.load_training_data(
            DisasterType.FLOOD,
            self.data_dir
        )
        
        # Verify shapes
        assert X.shape[0] == 100, "Should have 100 samples"
        assert X.shape[1] == len(REQUIRED_FEATURES[DisasterType.FLOOD]), \
            "Feature count should match required features"
        assert y.shape[0] == 100, "Target should have 100 values"
        assert len(feature_names) == X.shape[1], \
            "Feature names count should match feature columns"
    
    def test_train_model_completes_without_errors(self):
        """Test that model training completes successfully."""
        X, y, _ = self.trainer.load_training_data(DisasterType.EARTHQUAKE, self.data_dir)
        
        # Should complete without raising exceptions
        model, metrics = self.trainer.train_model(X, y)
        
        # Verify model is trained
        assert model is not None
        assert hasattr(model, 'predict')
        
        # Verify metrics are present
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert 'r2' in metrics
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0
    
    def test_save_model_creates_file(self):
        """Test that model saving creates a loadable file."""
        import joblib
        
        X, y, _ = self.trainer.load_training_data(DisasterType.FIRE, self.data_dir)
        model, _ = self.trainer.train_model(X, y)
        
        # Save model
        filepath = self.trainer.save_model(model, DisasterType.FIRE, self.models_dir)
        
        # Verify file exists
        assert os.path.exists(filepath), f"Model file not created at {filepath}"
        
        # Verify file is loadable
        loaded_model = joblib.load(filepath)
        assert loaded_model is not None
        assert hasattr(loaded_model, 'predict')
    
    def test_saved_model_can_make_predictions(self):
        """Test that saved and loaded models can make predictions."""
        import joblib
        
        X, y, feature_names = self.trainer.load_training_data(
            DisasterType.GAS_LEAK,
            self.data_dir
        )
        model, _ = self.trainer.train_model(X, y)
        
        # Save and reload model
        filepath = self.trainer.save_model(model, DisasterType.GAS_LEAK, self.models_dir)
        loaded_model = joblib.load(filepath)
        
        # Make prediction with loaded model
        test_sample = X[0:1]  # Take first sample
        prediction = loaded_model.predict(test_sample)
        
        # Verify prediction is valid
        assert len(prediction) == 1
        assert prediction[0] > 0, "Prediction should be positive"
    
    def test_train_all_models_creates_all_model_files(self):
        """Test that training all models creates files for each disaster type."""
        import joblib
        
        results = self.trainer.train_all_models(
            data_dir=self.data_dir,
            models_dir=self.models_dir
        )
        
        # Verify we have results for all disaster types
        assert len(results) == len(DisasterType), \
            f"Expected {len(DisasterType)} models, got {len(results)}"
        
        # Verify all model files exist and are loadable
        for disaster_type, result in results.items():
            filepath = result['filepath']
            assert os.path.exists(filepath), \
                f"Model file for {disaster_type} not found at {filepath}"
            
            # Verify model is loadable
            model = joblib.load(filepath)
            assert model is not None
            
            # Verify metrics are reasonable
            metrics = result['metrics']
            assert metrics['r2'] > 0.5, \
                f"R² score for {disaster_type} is too low: {metrics['r2']}"



# ============================================================================
# Property Test for ML Model Fallback
# ============================================================================

# Property 3: Rule Engine Fallback
# Validates: Requirements 2.3, 10.3
@settings(max_examples=100)
@given(disaster_type=disaster_types, features=st.data())
def test_property_3_ml_fallback_to_rule_engine(disaster_type, features):
    """
    Feature: disaster-impact-radius, Property 3: Rule Engine Fallback
    
    For any disaster type with valid features, predictions should succeed
    even when ML models fail to load or are unavailable. The system should
    automatically fall back to rule-based predictions.
    
    Validates: Requirements 2.3, 10.3
    """
    from impact_radius.ml_models import MLModelPredictor
    
    # Create predictor with non-existent models directory
    # This simulates the scenario where ML models are unavailable
    predictor = MLModelPredictor(models_dir="/nonexistent/path/to/models")
    
    # Generate valid features for the disaster type
    valid_feature_dict = features.draw(complete_valid_features(disaster_type))
    
    # Prediction should succeed using fallback
    radius = predictor.predict(disaster_type, valid_feature_dict, use_fallback=True)
    
    # Verify prediction is valid
    assert radius > 0, f"Radius should be positive, got {radius}"
    
    # Verify radius is within realistic bounds
    min_radius, max_radius = RADIUS_BOUNDS[disaster_type]
    assert min_radius <= radius <= max_radius, \
        f"Radius {radius} outside bounds [{min_radius}, {max_radius}] for {disaster_type}"
    
    # Verify that the model is reported as unavailable
    assert not predictor.is_model_available(disaster_type), \
        f"Model for {disaster_type} should be reported as unavailable"
