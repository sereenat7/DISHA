# Implementation Plan: Disaster Impact Radius Prediction System

## Overview

This implementation plan breaks down the disaster impact radius prediction system into discrete, incremental coding tasks. The system will be built as a new module within the existing Backend/ directory, integrating seamlessly with the current FastAPI application. Each task builds on previous work, with testing integrated throughout to catch errors early.

## Tasks

- [x] 1. Set up project structure and feature definitions
  - Create `Backend/impact_radius/` directory structure
  - Create `__init__.py` files for Python package structure
  - Define feature schemas and validation rules in `features.py`
  - Define disaster type constants and bounds
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 1.1 Write property test for feature validation
  - **Property 4: Feature Validation Completeness**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 10.1**
  - Test that missing required features for any disaster type raises validation error

- [x] 1.2 Write property test for feature range validation
  - **Property 5: Feature Range Validation**
  - **Validates: Requirements 10.2**
  - Test that out-of-range feature values raise validation errors

- [x] 2. Implement rule-based prediction engine
  - [x] 2.1 Create `rule_engine.py` with base RuleEngine class
    - Implement flood radius calculation formula
    - Implement earthquake radius calculation formula
    - Implement fire radius calculation formula
    - Implement cyclone radius calculation formula
    - Implement gas leak radius calculation formula
    - _Requirements: 2.1, 8.4_

- [x] 2.2 Write unit tests for rule engine formulas
  - Test each disaster type with known input/output examples
  - Test boundary conditions (min/max feature values)
  - Test edge cases (zero values, extreme values)
  - _Requirements: 2.1_

- [x] 2.3 Write property test for disaster type support
  - **Property 1: Disaster Type Support Completeness**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
  - Test that all supported disaster types return valid predictions

- [x] 2.4 Write property test for unsupported disaster types
  - **Property 2: Unsupported Disaster Type Rejection**
  - **Validates: Requirements 1.6**
  - Test that invalid disaster types raise descriptive errors

- [x] 3. Implement ML model training pipeline
  - [x] 3.1 Create `training/synthetic_data.py` for data generation
    - Generate 1000 samples per disaster type using rule engine
    - Add Gaussian noise (mean=0, std=0.15 * rule_prediction)
    - Save to CSV files in `training/data/` directory
    - _Requirements: 2.2, 8.5_

  - [x] 3.2 Create `training/train_models.py` for model training
    - Load synthetic training data
    - Train RandomForestRegressor for each disaster type (100 trees, max_depth=10)
    - Evaluate models using train-test split (80/20)
    - Save trained models to `models/` directory using joblib
    - _Requirements: 2.2_

- [x] 3.3 Write unit tests for training pipeline
  - Test synthetic data generation produces valid samples
  - Test model training completes without errors
  - Test model files are created and loadable
  - _Requirements: 2.2_

- [x] 4. Implement ML model wrapper
  - [x] 4.1 Create `ml_models.py` with MLModelPredictor class
    - Implement model loading from joblib files
    - Implement prediction method with feature vector input
    - Implement fallback handling when model unavailable
    - Cache loaded models in memory
    - _Requirements: 2.2, 2.3, 10.3_

- [x] 4.2 Write property test for ML fallback behavior
  - **Property 3: Rule Engine Fallback**
  - **Validates: Requirements 2.3, 10.3**
  - Test that predictions succeed even when ML models fail to load

- [ ] 5. Checkpoint - Ensure all tests pass
  - Run all unit tests and property tests
  - Verify rule engine and ML models work independently
  - Ensure all tests pass, ask the user if questions arise

- [ ] 6. Implement ensemble combination logic
  - [ ] 6.1 Create `ensemble.py` with EnsembleCombiner class
    - Implement adaptive weighting based on data availability
    - Implement confidence score calculation (agreement + data + features)
    - Implement risk level classification (low/moderate/high/critical)
    - Implement explanation text generation
    - _Requirements: 2.5, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 7.1, 7.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 6.2 Write property test for ensemble weight consistency
  - **Property 15: Ensemble Weight Consistency**
  - **Validates: Requirements 2.5**
  - Test that rule_weight + ml_weight = 1.0 for all predictions

- [ ] 6.3 Write property test for confidence score bounds
  - **Property 7: Confidence Score Bounds**
  - **Validates: Requirements 4.2, 9.5**
  - Test that confidence is always between 0.0 and 1.0

- [ ] 6.4 Write property test for confidence and prediction agreement
  - **Property 11: Confidence Decreases with Divergence**
  - **Validates: Requirements 9.4**
  - Test that divergent predictions result in lower confidence

- [ ] 6.5 Write property test for risk level classification
  - **Property 8: Risk Level Classification**
  - **Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.7**
  - Test that risk_level is always one of: low, moderate, high, critical

- [ ] 6.6 Write unit tests for risk level thresholds
  - Test specific radius values map to correct risk levels
  - Test disaster-specific risk adjustments (e.g., magnitude > 7 = critical)
  - _Requirements: 4.4, 4.5, 4.6, 4.7_

- [ ] 7. Implement main prediction orchestrator
  - [ ] 7.1 Create `predictor.py` with ImpactRadiusPredictor class
    - Implement prediction pipeline (validate → rule → ML → ensemble)
    - Implement realistic bounds enforcement per disaster type
    - Implement GeoJSON output generation
    - Implement error handling and logging
    - _Requirements: 4.1, 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 10.5_

- [ ] 7.2 Write property test for radius positivity
  - **Property 9: Radius Positivity**
  - **Validates: Requirements 6.3**
  - Test that predicted radius is always positive and non-zero

- [ ] 7.3 Write property test for realistic bounds
  - **Property 10: Realistic Bounds Enforcement**
  - **Validates: Requirements 8.1, 8.2, 8.3**
  - Test that radius is within min/max bounds for each disaster type

- [ ] 7.4 Write property test for output completeness
  - **Property 6: Output Completeness**
  - **Validates: Requirements 4.1, 4.2, 4.3, 4.8, 5.6, 5.7**
  - Test that all required fields are present in prediction response

- [ ] 7.5 Write property test for explanation non-empty
  - **Property 12: Explanation Non-Empty**
  - **Validates: Requirements 7.1**
  - Test that explanation field is always non-empty

- [ ] 7.6 Write property test for coordinate validity
  - **Property 14: Coordinate Validity**
  - **Validates: Requirements 5.2, 6.1**
  - Test that latitude is in [-90, 90] and longitude in [-180, 180]

- [ ] 8. Checkpoint - Ensure all tests pass
  - Run complete test suite
  - Verify end-to-end prediction flow works
  - Ensure all tests pass, ask the user if questions arise

- [ ] 9. Create Pydantic models for API
  - [ ] 9.1 Define ImpactRadiusPredictionRequest model in `features.py`
    - Add disaster_type, latitude, longitude, features fields
    - Add field validators and examples
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 9.2 Define ImpactRadiusPredictionResponse model in `features.py`
    - Add all output fields (radius, confidence, risk_level, etc.)
    - Add GeoJSON structure
    - Add response examples
    - _Requirements: 4.1, 4.2, 4.3, 4.8, 5.6, 5.7, 6.4_

- [ ]* 9.3 Write property test for GeoJSON validity
  - **Property 13: GeoJSON Format Validity**
  - **Validates: Requirements 6.4**
  - Test that geojson field contains valid GeoJSON Feature structure

- [ ] 10. Integrate with FastAPI application
  - [ ] 10.1 Add impact radius endpoint to `Backend/app.py`
    - Import predictor and models
    - Create POST endpoint at `/api/predict-impact-radius`
    - Implement request validation and error handling
    - Return structured JSON response
    - Update root endpoint to include new endpoint in list
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 10.1, 10.2, 10.4_

  - [ ] 10.2 Update `Backend/requirements.txt`
    - Add scikit-learn==1.3.2
    - Add joblib==1.3.2
    - Add numpy==1.24.3
    - Add hypothesis==6.92.1 (for property-based testing)
    - _Requirements: All_

- [ ]* 10.3 Write integration tests for API endpoint
  - Test successful prediction request returns 200
  - Test invalid disaster type returns 400
  - Test missing features returns 400
  - Test out-of-range coordinates returns 400
  - Test response format matches schema
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 11. Generate training data and train models
  - [ ] 11.1 Run synthetic data generation script
    - Execute `python Backend/impact_radius/training/synthetic_data.py`
    - Verify CSV files created in `training/data/` directory
    - _Requirements: 2.2, 8.5_

  - [ ] 11.2 Run model training script
    - Execute `python Backend/impact_radius/training/train_models.py`
    - Verify model files created in `models/` directory
    - Review training metrics (RMSE, R²)
    - _Requirements: 2.2_

- [ ] 12. Final checkpoint and documentation
  - [ ] 12.1 Run complete test suite
    - Execute `pytest Backend/tests/test_impact_radius.py -v`
    - Ensure all unit tests pass
    - Ensure all property tests pass (100+ iterations each)
    - _Requirements: All_

  - [ ] 12.2 Test API endpoint manually
    - Start FastAPI server: `uvicorn Backend.app:app --reload`
    - Test with curl or Postman for each disaster type
    - Verify GeoJSON output format
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ] 12.3 Create API documentation examples
    - Add example requests for each disaster type to docstrings
    - Document feature requirements per disaster type
    - Document response format and GeoJSON structure
    - _Requirements: All_

- [ ] 13. Integration with existing system
  - [ ] 13.1 Test combined workflow
    - Test impact radius prediction → evacuation routing integration
    - Verify radius can be used as input to evacuation system
    - Test with realistic disaster scenarios
    - _Requirements: All_

  - [ ] 13.2 Update health check endpoint
    - Add impact radius system status to `/health` endpoint
    - Check if ML models are loaded
    - Report system readiness
    - _Requirements: All_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (100+ iterations)
- Unit tests validate specific examples and edge cases
- The system integrates seamlessly with existing Backend/app.py
- Initial deployment uses synthetic training data; replace with real data in production
- All ML models have fallback to rule-based predictions for robustness
