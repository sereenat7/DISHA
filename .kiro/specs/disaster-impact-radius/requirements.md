# Requirements Document

## Introduction

The Disaster Impact Radius Prediction Engine is a fully automated, zero-user-input system that predicts geographical impact zones for active disasters in real-time. Designed for stressed, panicking users who cannot provide detailed inputs, the system autonomously fetches data from external sources (weather APIs, seismic feeds, satellite data, public alerts) and combines rule-based heuristics with machine learning regression to generate accurate, explainable impact radius predictions. These predictions enable the Emergency Route Builder (ERB) to calculate safe evacuation routes and help emergency responders visualize threat zones on maps. The system must be implementable as an MVP within approximately 1 hour and be defensible in technical reviews.

## Glossary

- **Prediction_Engine**: The automated system that calculates disaster impact zones without user input
- **Disaster_Type**: Classification of disaster (flood, earthquake, fire, cyclone, gas_leak)
- **External_Data_Source**: APIs, feeds, or datasets accessed automatically (weather, seismic, satellite, alerts)
- **Confidence_Score**: A numerical value (0-1) indicating prediction reliability
- **Risk_Level**: Categorical assessment (low, moderate, high, critical) of disaster severity
- **Threat_Zone**: Circular geographical area affected by the disaster
- **Rule_Engine**: Component implementing physics-based heuristics as safety baseline
- **ML_Regressor**: Machine learning model that refines predictions when sufficient data exists
- **Hybrid_Approach**: Weighted combination of Rule_Engine and ML_Regressor outputs
- **Method_Used**: Indicator of which approach was used (rule_based, ml_based, hybrid)
- **Feature_Extractor**: Component that automatically extracts relevant parameters from External_Data_Source
- **ERB**: Emergency Route Builder that consumes impact radius predictions
- **GeoJSON**: Geographic data format for map visualization
- **Conservative_Fallback**: Safe default prediction when data is unavailable or uncertain

## Requirements

### Requirement 1: Zero-User-Input Operation

**User Story:** As a panicking citizen during a disaster, I want the system to work automatically without requiring me to input complex data, so that I can get evacuation guidance immediately.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL operate without requiring manual user input for disaster parameters
2. THE Prediction_Engine SHALL automatically detect active disasters from External_Data_Source
3. WHEN user location is available, THEN THE Prediction_Engine SHALL use it as the disaster epicenter
4. WHEN user location is unavailable, THEN THE Prediction_Engine SHALL use disaster epicenter from External_Data_Source
5. THE Prediction_Engine SHALL fetch all required data autonomously from External_Data_Source

### Requirement 2: External Data Source Integration

**User Story:** As a disaster management systems engineer, I want the system to pull data from reliable external sources, so that predictions are based on real-time authoritative information.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL integrate with weather APIs for meteorological data
2. THE Prediction_Engine SHALL integrate with seismic APIs for earthquake data
3. THE Prediction_Engine SHALL integrate with satellite feeds for fire and flood monitoring
4. THE Prediction_Engine SHALL integrate with public alert systems for verified disaster notifications
5. THE Prediction_Engine SHALL integrate with news APIs for disaster event detection
6. WHEN an External_Data_Source is unavailable, THEN THE Prediction_Engine SHALL use Conservative_Fallback values
7. THE Prediction_Engine SHALL cache recent data to handle temporary API failures

### Requirement 3: Multi-Disaster Type Support

**User Story:** As an emergency response coordinator, I want the system to handle multiple disaster types, so that I can respond appropriately to any emergency scenario.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL support flood disaster predictions
2. THE Prediction_Engine SHALL support earthquake disaster predictions
3. THE Prediction_Engine SHALL support fire disaster predictions
4. THE Prediction_Engine SHALL support cyclone disaster predictions
5. THE Prediction_Engine SHALL support gas_leak disaster predictions
6. WHEN disaster type cannot be determined, THEN THE Prediction_Engine SHALL use the most conservative radius estimate

### Requirement 4: Disaster-Specific Feature Extraction

**User Story:** As a data scientist, I want each disaster type to use scientifically relevant parameters, so that predictions are physically accurate and defensible.

#### Acceptance Criteria

1. WHEN predicting flood impact, THEN THE Feature_Extractor SHALL extract rainfall intensity, duration, elevation data, and river proximity from External_Data_Source
2. WHEN predicting earthquake impact, THEN THE Feature_Extractor SHALL extract magnitude, depth, and soil type from External_Data_Source
3. WHEN predicting fire impact, THEN THE Feature_Extractor SHALL extract fire intensity, wind speed, wind direction, humidity, and temperature from External_Data_Source
4. WHEN predicting cyclone impact, THEN THE Feature_Extractor SHALL extract wind speed, atmospheric pressure, movement speed, and coastal proximity from External_Data_Source
5. WHEN predicting gas_leak impact, THEN THE Feature_Extractor SHALL extract wind speed, atmospheric stability, and estimated leak severity from External_Data_Source
6. THE Feature_Extractor SHALL ignore irrelevant parameters for each disaster type

### Requirement 5: Hybrid Prediction Approach

**User Story:** As a disaster management systems engineer, I want the system to use both rule-based heuristics and machine learning, so that predictions are safe even with limited data and accurate when data is abundant.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL implement a Rule_Engine with physics-based heuristics as a safety baseline
2. THE Prediction_Engine SHALL implement ML_Regressor models trained on historical disaster datasets
3. WHEN sufficient real-time data is available, THEN THE Prediction_Engine SHALL use Hybrid_Approach combining Rule_Engine and ML_Regressor
4. WHEN real-time data is insufficient, THEN THE Prediction_Engine SHALL rely primarily on Rule_Engine
5. WHEN ML_Regressor confidence is high, THEN THE Prediction_Engine SHALL weight ML_Regressor predictions more heavily
6. WHEN Rule_Engine and ML_Regressor predictions diverge significantly, THEN THE Prediction_Engine SHALL use the more conservative (larger) radius

### Requirement 6: Comprehensive Prediction Output

**User Story:** As an emergency operations center operator, I want detailed prediction outputs, so that I can assess the situation and coordinate responses effectively.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL output impact radius in kilometers
2. THE Prediction_Engine SHALL output Confidence_Score between 0.0 and 1.0
3. THE Prediction_Engine SHALL output Risk_Level as one of: low, moderate, high, critical
4. THE Prediction_Engine SHALL output Method_Used as one of: rule_based, ml_based, hybrid
5. THE Prediction_Engine SHALL output human-readable explanation text describing the prediction rationale
6. THE Prediction_Engine SHALL output disaster epicenter coordinates (latitude, longitude)
7. THE Prediction_Engine SHALL output timestamp of prediction generation

### Requirement 7: Explainability and Transparency

**User Story:** As a disaster response team leader, I want to understand how the system made its prediction, so that I can trust the recommendations and explain them to stakeholders.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL generate human-readable explanation for every prediction
2. WHEN using Rule_Engine, THEN THE Prediction_Engine SHALL explain which heuristic rules were applied
3. WHEN using ML_Regressor, THEN THE Prediction_Engine SHALL identify the most influential features
4. WHEN using Hybrid_Approach, THEN THE Prediction_Engine SHALL indicate the relative weight of Rule_Engine versus ML_Regressor
5. THE Prediction_Engine SHALL include data source information in the explanation
6. THE Prediction_Engine SHALL indicate confidence level reasoning in the explanation

### Requirement 8: RESTful FastAPI Interface

**User Story:** As a frontend developer, I want well-defined API endpoints, so that I can integrate the prediction engine with the ERB and map visualization.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL expose a GET endpoint at "/api/disaster/impact-radius"
2. THE Prediction_Engine SHALL accept optional query parameters: disaster_type, latitude, longitude
3. WHEN disaster_type is not provided, THEN THE Prediction_Engine SHALL auto-detect from External_Data_Source
4. WHEN coordinates are not provided, THEN THE Prediction_Engine SHALL use user's current location or detected disaster epicenter
5. WHEN prediction succeeds, THEN THE Prediction_Engine SHALL return HTTP 200 with JSON response
6. WHEN prediction fails, THEN THE Prediction_Engine SHALL return appropriate HTTP error code with error details
7. THE Prediction_Engine SHALL return response within 3 seconds for real-time usability

### Requirement 9: Map Visualization Support

**User Story:** As a situation room analyst, I want to visualize the impact radius as a circular danger zone on a map, so that I can quickly assess affected areas.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL output GeoJSON-compatible format for map rendering
2. THE Prediction_Engine SHALL include center coordinates and radius for circular Threat_Zone
3. THE Prediction_Engine SHALL ensure radius is a positive non-zero value
4. THE Prediction_Engine SHALL include risk_level for color-coding the Threat_Zone on maps
5. THE Prediction_Engine SHALL provide bounding box coordinates for map viewport adjustment

### Requirement 10: Realistic and Validated Predictions

**User Story:** As a disaster management authority, I want predictions to be realistic and scientifically defensible, so that emergency responses are appropriately scaled and justifiable.

#### Acceptance Criteria

1. THE Rule_Engine SHALL implement formulas based on established disaster science literature
2. THE Prediction_Engine SHALL enforce minimum radius constraints per disaster type (e.g., earthquake minimum 1 km)
3. THE Prediction_Engine SHALL enforce maximum radius constraints per disaster type (e.g., gas leak maximum 10 km)
4. WHEN predicted radius exceeds realistic bounds, THEN THE Prediction_Engine SHALL cap the value and reduce Confidence_Score
5. THE ML_Regressor SHALL be trained only on verified historical disaster datasets from authoritative sources

### Requirement 11: Confidence Score Calculation

**User Story:** As a risk analyst, I want to know how confident the system is in its predictions, so that I can adjust response plans and communicate uncertainty appropriately.

#### Acceptance Criteria

1. WHEN External_Data_Source provides complete and recent data, THEN THE Prediction_Engine SHALL assign higher Confidence_Score
2. WHEN External_Data_Source data is incomplete or stale, THEN THE Prediction_Engine SHALL assign lower Confidence_Score
3. WHEN Rule_Engine and ML_Regressor predictions agree closely, THEN THE Prediction_Engine SHALL assign higher Confidence_Score
4. WHEN predictions diverge significantly, THEN THE Prediction_Engine SHALL assign lower Confidence_Score
5. WHEN using Conservative_Fallback values, THEN THE Prediction_Engine SHALL assign Confidence_Score below 0.5
6. THE Confidence_Score SHALL be normalized to a range of 0.0 to 1.0

### Requirement 12: Error Handling and Conservative Fallbacks

**User Story:** As a system administrator, I want the system to handle errors gracefully and fail safely, so that users always receive a prediction even when data sources are unavailable.

#### Acceptance Criteria

1. WHEN External_Data_Source is unavailable, THEN THE Prediction_Engine SHALL use Conservative_Fallback values
2. WHEN ML_Regressor fails to load, THEN THE Prediction_Engine SHALL fall back to Rule_Engine only
3. WHEN disaster type cannot be determined, THEN THE Prediction_Engine SHALL use the largest reasonable radius across all disaster types
4. WHEN prediction computation fails, THEN THE Prediction_Engine SHALL return HTTP 500 with error details and suggested fallback radius
5. THE Prediction_Engine SHALL log all errors for debugging and monitoring
6. THE Prediction_Engine SHALL never return a prediction with radius of zero

### Requirement 13: MVP Implementation Feasibility

**User Story:** As a project manager, I want the system to be implementable within a short development window, so that we can demonstrate a working prototype quickly.

#### Acceptance Criteria

1. THE Prediction_Engine SHALL use publicly available External_Data_Source with free API tiers
2. THE Rule_Engine SHALL implement simple, well-documented heuristic formulas
3. THE ML_Regressor SHALL use lightweight models (e.g., linear regression, decision trees) that train quickly
4. THE Prediction_Engine SHALL use standard Python libraries (scikit-learn, requests, FastAPI)
5. THE Prediction_Engine SHALL include mock data generators for testing when External_Data_Source is unavailable during development
