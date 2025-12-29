# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from Disaster.trigger import trigger_disaster
from News.info import get_current_natural_disasters

app = FastAPI(
    title="Disaster Management API",
    description="Trigger disasters & fetch real-time natural disaster news",
    version="1.0.0"
)

# Enable CORS for frontend (React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DisasterTriggerRequest(BaseModel):
    type: str = Field(..., description="Type of disaster")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(default=1000, ge=100)

@app.post("/disaster/trigger")
async def api_trigger_disaster(request: DisasterTriggerRequest):
    try:
        result = trigger_disaster(
            disaster_type=request.type,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.radius_meters
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/news/disasters")
async def api_get_disasters():
    return get_current_natural_disasters()

@app.get("/")
async def root():
    return {"message": "Disaster Management Backend Running!", "docs": "/docs"}