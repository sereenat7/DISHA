# Disaster/trigger.py
from datetime import datetime

DISASTER_TYPES = [
    "Flood", "Earthquake", "Fire", "Terrorist Attack", "Cyclone",
    "Tsunami", "Landslide", "Chemical Spill", "Nuclear Incident",
    "Volcanic Eruption", "Heatwave", "Biological Hazard"
]


def trigger_disaster(disaster_type: str, latitude: float, longitude: float, radius_meters: int = 1000):
    if disaster_type not in DISASTER_TYPES:
        raise ValueError(
            f"Invalid type. Choose from: {', '.join(DISASTER_TYPES)}")
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude must be between -180 and 180")
    if radius_meters < 100:
        raise ValueError("Radius must be >= 100 meters")

    return {
        "id": "simulated-disaster-12345",
        "type": disaster_type,
        "latitude": latitude,
        "longitude": longitude,
        "radius_meters": radius_meters,
        "address": None,
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "message": "Disaster trigger successful! Danger zone activated."
    }
