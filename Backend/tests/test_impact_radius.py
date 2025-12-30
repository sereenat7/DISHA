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
    validate_features,
    FeatureValidationError,
    ImpactRadiusPredictionRequest,
)


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
