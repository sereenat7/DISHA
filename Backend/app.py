from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime

# Existing alerts
from Asycn_Alerts.alerts import send_parallel_alerts, logger

# Evacuation logic import
from evacuation_system.main import find_evacuation_routes

# Impact radius prediction import
from impact_radius.predictor import ImpactRadiusPredictor
from impact_radius.features import (
    ImpactRadiusPredictionRequest,
    ImpactRadiusPredictionResponse,
    FeatureValidationError
)

app = FastAPI(
    title="DISHA - Disaster Intelligence Safety & Help Application",
    description="Emergency Alert + Dynamic Evacuation Routing System using OSM & OSRM",
    version="1.0.0"
)

# -----------------------------
# Initialize Impact Radius Predictor
# -----------------------------
impact_predictor = ImpactRadiusPredictor()

# -----------------------------
# ✅ CORS POLICY (GITHUB FIX)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Root & Health
# -----------------------------
@app.get("/")
def read_root():
    return {
        "service": "DISHA Alert & Evacuation System",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "trigger_alerts": "/api/alerts/trigger",
            "trigger_evacuation": "/api/evacuation/trigger",
            "predict_impact_radius": "/api/predict-impact-radius",
            "health": "/health"
        }
    }


@app.get("/health")
def health_check():
    twilio_configured = all([
        os.environ.get('TWILIO_ACCOUNT_SID'),
        os.environ.get('TWILIO_AUTH_TOKEN'),
        os.environ.get('TWILIO_PHONE_NUMBER')
    ])
    
    # Get impact radius system status
    impact_status = impact_predictor.get_system_status()

    return {
        "status": "healthy" if twilio_configured else "configuration_incomplete",
        "twilio_configured": twilio_configured,
        "overpass_osrm_reachable": True,
        "impact_radius_system": impact_status,
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------
# Twilio Alerts
# -----------------------------
@app.get("/api/alerts/trigger")
def trigger_alerts():
    try:
        twilio_configured = all([
            os.environ.get('TWILIO_ACCOUNT_SID'),
            os.environ.get('TWILIO_AUTH_TOKEN'),
            os.environ.get('TWILIO_PHONE_NUMBER')
        ])

        if not twilio_configured:
            raise HTTPException(
                status_code=500,
                detail="Twilio credentials not configured."
            )

        contacts = [
            {
                'phone': '+918850755760',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            },
            {
                'phone': '+919529685725',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            },
            {
                'phone': '+919322945843',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            }
        ]

        logger.info("Alert trigger received via API")

        results = send_parallel_alerts(
            contacts,
            max_workers=5,
            num_call_attempts=1,
            wait_time_between_rounds=10
        )

        formatted_results = []
        for result in results:
            calls = result.get('calls', [])
            successful_calls = sum(1 for c in calls if c.get('success'))

            formatted_results.append({
                "phone": result.get('phone'),
                "total_calls": len(calls),
                "successful_calls": successful_calls,
                "sms_sent": result.get('sms', {}).get('success', False),
                "call_details": calls
            })

        return {
            "status": "completed",
            "message": "Alerts sent successfully",
            "total_contacts": len(results),
            "timestamp": datetime.now().isoformat(),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"Error triggering alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# -----------------------------
# Evacuation Routes
# -----------------------------
@app.post("/api/evacuation/trigger")
async def trigger_evacuation(
    user_id: str = Body(..., embed=True),
    user_lat: float = Body(..., embed=True),
    user_lon: float = Body(..., embed=True),
    radius_km: float = Body(10.0, embed=True),
):
    try:
        if not (-90 <= user_lat <= 90):
            raise HTTPException(status_code=400, detail="Invalid latitude.")
        if not (-180 <= user_lon <= 180):
            raise HTTPException(status_code=400, detail="Invalid longitude.")
        if radius_km <= 0 or radius_km > 50:
            raise HTTPException(status_code=400, detail="Radius must be between 0 and 50 km.")

        logger.info(
            f"Evacuation request for user {user_id} "
            f"at ({user_lat}, {user_lon}), radius {radius_km}km"
        )

        evacuation_data = await find_evacuation_routes(
            user_lat=user_lat,
            user_lon=user_lon,
            radius_km=radius_km,
            max_per_category=2
        )

        return JSONResponse(content={
            "status": "success",
            "user_id": user_id,
            "alert_id": evacuation_data["alert_id"],
            "timestamp": datetime.now().isoformat(),
            "evacuation_routes": evacuation_data["results"]
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evacuation routing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to compute evacuation routes."
        )


# -----------------------------
# Impact Radius Prediction
# -----------------------------
@app.post("/api/predict-impact-radius", response_model=ImpactRadiusPredictionResponse)
async def predict_impact_radius(request: ImpactRadiusPredictionRequest):
    """
    Predict the impact radius for a disaster event.
    
    This endpoint uses a hybrid approach combining rule-based heuristics and 
    machine learning models to predict the geographical impact zone of a disaster.
    
    ## Supported Disaster Types
    
    - **flood**: Requires rainfall_intensity, duration, elevation, river_proximity
    - **earthquake**: Requires magnitude, depth, soil_type
    - **fire**: Requires fire_intensity, wind_speed, wind_direction, humidity, temperature
    - **cyclone**: Requires wind_speed, atmospheric_pressure, movement_speed, coastal_proximity
    - **gas_leak**: Requires wind_speed, atmospheric_stability, leak_severity
    
    ## Feature Requirements by Disaster Type
    
    ### Flood
    - `rainfall_intensity` (float): Rainfall intensity in mm/hour (0-500)
    - `duration` (float): Duration in hours (0-168)
    - `elevation` (float): Elevation in meters (-500 to 9000)
    - `river_proximity` (float): Distance to nearest river in km (0-100)
    
    ### Earthquake
    - `magnitude` (float): Richter scale magnitude (0-10)
    - `depth` (float): Depth in kilometers (0-700)
    - `soil_type` (float): Soil type category (1=rock, 2=dense_soil, 3=soft_soil, 4=sand, 5=fill)
    
    ### Fire
    - `fire_intensity` (float): Fire intensity scale (0-100)
    - `wind_speed` (float): Wind speed in km/h (0-200)
    - `wind_direction` (float): Wind direction in degrees (0-360)
    - `humidity` (float): Relative humidity percentage (0-100)
    - `temperature` (float): Temperature in Celsius (-50 to 60)
    
    ### Cyclone
    - `wind_speed` (float): Wind speed in km/h (0-200)
    - `atmospheric_pressure` (float): Atmospheric pressure in hPa (870-1050)
    - `movement_speed` (float): Cyclone movement speed in km/h (0-100)
    - `coastal_proximity` (float): Distance to coast in km (0-1000)
    
    ### Gas Leak
    - `wind_speed` (float): Wind speed in km/h (0-200)
    - `atmospheric_stability` (float): Pasquill stability class (1=very unstable to 6=very stable)
    - `leak_severity` (float): Leak severity scale (1-10)
    
    ## Request Examples
    
    ### Earthquake Example
    ```json
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
    ```
    
    ### Flood Example
    ```json
    {
      "disaster_type": "flood",
      "latitude": 19.1337,
      "longitude": 72.8611,
      "features": {
        "rainfall_intensity": 50.0,
        "duration": 12.0,
        "elevation": 10.0,
        "river_proximity": 2.0
      }
    }
    ```
    
    ### Fire Example
    ```json
    {
      "disaster_type": "fire",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "features": {
        "fire_intensity": 75.0,
        "wind_speed": 30.0,
        "wind_direction": 180.0,
        "humidity": 20.0,
        "temperature": 35.0
      }
    }
    ```
    
    ### Cyclone Example
    ```json
    {
      "disaster_type": "cyclone",
      "latitude": 20.0,
      "longitude": 85.0,
      "features": {
        "wind_speed": 150.0,
        "atmospheric_pressure": 950.0,
        "movement_speed": 20.0,
        "coastal_proximity": 50.0
      }
    }
    ```
    
    ### Gas Leak Example
    ```json
    {
      "disaster_type": "gas_leak",
      "latitude": 28.6139,
      "longitude": 77.2090,
      "features": {
        "wind_speed": 15.0,
        "atmospheric_stability": 3.0,
        "leak_severity": 7.0
      }
    }
    ```
    
    ## Response Format
    
    The response includes:
    - `radius_km`: Predicted impact radius in kilometers (always positive)
    - `confidence_score`: Confidence level between 0.0 and 1.0
    - `risk_level`: Classification as "low", "moderate", "high", or "critical"
    - `method_used`: Prediction method ("rule_based", "ml_based", or "hybrid")
    - `explanation`: Human-readable explanation of the prediction
    - `epicenter`: Disaster epicenter coordinates (latitude, longitude)
    - `timestamp`: ISO 8601 timestamp of prediction generation
    - `geojson`: GeoJSON Feature for map visualization with Point geometry
    
    ### Response Example
    ```json
    {
      "radius_km": 25.74,
      "confidence_score": 0.85,
      "risk_level": "high",
      "method_used": "hybrid",
      "explanation": "Earthquake magnitude 6.5 at shallow depth (10km) in soft soil area...",
      "epicenter": {"latitude": 34.05, "longitude": -118.25},
      "timestamp": "2024-01-15T10:30:00Z",
      "geojson": {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [-118.25, 34.05]
        },
        "properties": {
          "radius_km": 25.74,
          "risk_level": "high",
          "disaster_type": "earthquake"
        }
      }
    }
    ```
    
    ## GeoJSON Structure
    
    The `geojson` field contains a valid GeoJSON Feature with:
    - **geometry.type**: Always "Point"
    - **geometry.coordinates**: [longitude, latitude] (note: GeoJSON uses lon, lat order)
    - **properties.radius_km**: Impact radius for drawing circles on maps
    - **properties.risk_level**: For color-coding threat zones
    - **properties.disaster_type**: Type of disaster
    
    Use the center point and radius to draw circular threat zones on mapping libraries
    like Leaflet, Mapbox, or Google Maps.
    
    ## Error Responses
    
    ### 400 Bad Request - Missing Features
    ```json
    {
      "detail": [
        {
          "type": "value_error",
          "loc": ["body"],
          "msg": "Value error, Missing required features for earthquake: ['soil_type']"
        }
      ]
    }
    ```
    
    ### 400 Bad Request - Invalid Coordinates
    ```json
    {
      "detail": [
        {
          "type": "less_than_equal",
          "loc": ["body", "latitude"],
          "msg": "Input should be less than or equal to 90"
        }
      ]
    }
    ```
    
    ### 400 Bad Request - Out of Range Feature
    ```json
    {
      "detail": "Feature validation error: Feature 'magnitude' value 15.0 is out of valid range [0.0, 10.0]"
    }
    ```
    
    ### 500 Internal Server Error
    ```json
    {
      "detail": "Internal server error: Failed to predict impact radius"
    }
    ```
    
    Args:
        request: Prediction request containing disaster type, location, and features
        
    Returns:
        Prediction response with radius, confidence score, risk level, and GeoJSON
        
    Raises:
        400: Invalid input (missing features, out-of-range values, unsupported disaster type)
        500: Internal prediction error
    """
    try:
        logger.info(
            f"Impact radius prediction request: {request.disaster_type.value} "
            f"at ({request.latitude}, {request.longitude})"
        )
        
        # Perform prediction
        response = impact_predictor.predict_from_request(request)
        
        logger.info(
            f"Prediction successful: radius={response.radius_km:.2f}km, "
            f"confidence={response.confidence_score:.2f}, risk={response.risk_level.value}"
        )
        
        return response
        
    except FeatureValidationError as e:
        logger.error(f"Feature validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Feature validation error: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Impact radius prediction failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: Failed to predict impact radius"
        )


# -----------------------------19.1337, 72.8611


# Run Server
# -----------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
