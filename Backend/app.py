from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
import os
from datetime import datetime

# Existing imports
from Asycn_Alerts.alerts import send_parallel_alerts, logger
from evacuation_system.main import find_evacuation_routes


app = FastAPI(
    title="DISHA - Disaster Intelligence Safety & Help Application",
    description="Emergency Alert + Dynamic Evacuation Routing System using OSM & OSRM",
    version="1.0.0"
)

# -----------------------------
# CORS Configuration (Works perfectly on Render)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# -----------------------------
# Pydantic Models
# -----------------------------
class EvacuationRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    user_lat: float = Field(..., description="Latitude of user's location")
    user_lon: float = Field(..., description="Longitude of user's location")
    radius_km: float = Field(10.0, ge=0.1, le=50, description="Search radius in kilometers")

    @validator('user_lat')
    def validate_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('user_lon')
    def validate_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v


# -----------------------------
# Root & Health Endpoints
# -----------------------------
@app.get("/")
def read_root():
    return {
        "service": "DISHA Alert & Evacuation System",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "trigger_alerts": "POST /api/alerts/trigger",
            "trigger_evacuation": "POST /api/evacuation/trigger",
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
    return {
        "status": "healthy" if twilio_configured else "configuration_incomplete",
        "twilio_configured": twilio_configured,
        "overpass_osrm_reachable": True,
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------
# Alert Trigger Endpoint (Now POST)
# -----------------------------
@app.post("/api/alerts/trigger")
async def trigger_alerts():
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

        logger.info("Alert trigger received via API (POST)")
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
# Evacuation Routes Endpoint
# -----------------------------
@app.post("/api/evacuation/trigger")
async def trigger_evacuation(request: EvacuationRequest):
    try:
        logger.info(
            f"Evacuation request for user {request.user_id} "
            f"at ({request.user_lat}, {request.user_lon}), radius {request.radius_km}km"
        )

        evacuation_data = await find_evacuation_routes(
            user_lat=request.user_lat,
            user_lon=request.user_lon,
            radius_km=request.radius_km,
            max_per_category=2
        )

        return JSONResponse(content={
            "status": "success",
            "user_id": request.user_id,
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
# Run Server (Render Compatible)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app:app",  # This assumes the file is named app.py
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production (Render)
    )