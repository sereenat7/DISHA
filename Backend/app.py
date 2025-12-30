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
