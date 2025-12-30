# evacuation_logic.py
import httpx
import uuid
import math
import asyncio
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# Initialize FastAPI app
app = FastAPI(title="Evacuation System API", version="1.0.0")


# Pydantic models for API requests and responses
class DisasterEventRequest(BaseModel):
    """Request model for triggering disaster events."""
    disaster_type: str
    location_lat: float
    location_lon: float
    severity: str
    affected_radius_km: float = 5.0
    description: Optional[str] = None
    estimated_affected_population: Optional[int] = None


class DisasterEventResponse(BaseModel):
    """Response model for disaster event processing."""
    disaster_id: str
    status: str
    message: str
    processing_started_at: str
    estimated_completion_time: Optional[str] = None


class EvacuationRequest(BaseModel):
    """Request model for evacuation route finding."""
    user_lat: float
    user_lon: float
    radius_km: float = 10.0
    max_per_category: int = 2


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth (in kilometers).
    """
    R = 6371  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


async def get_safe_locations(lat: float, lon: float, radius_km: float):
    """
    Fetch safe locations (hospitals, shelters/bunkers, underground parking) around a point using Overpass API.
    """
    # Limit radius to prevent timeouts
    max_radius_km = 15.0
    if radius_km > max_radius_km:
        print(
            f"Warning: Radius {radius_km}km too large, limiting to {max_radius_km}km")
        radius_km = max_radius_km

    radius_m = int(radius_km * 1000)

    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="shelter"](around:{radius_m},{lat},{lon});
      node["building"="bunker"](around:{radius_m},{lat},{lon});
      node["amenity"="parking"]["parking"="underground"](around:{radius_m},{lat},{lon});
    );
    out body;
    """

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(OVERPASS_URL, data=query)

        if response.status_code != 200:
            print(
                f"Overpass API error: {response.status_code} - {response.text[:200]}")
            return await _get_fallback_locations(lat, lon, radius_km)

        if not response.text.strip():
            print("Overpass API returned empty response")
            return await _get_fallback_locations(lat, lon, radius_km)

    except Exception as e:
        print(f"Overpass API request failed: {e}")
        return await _get_fallback_locations(lat, lon, radius_km)

    data = response.json()
    locations = []

    for element in data.get("elements", []):
        el_lat = element.get("lat")
        el_lon = element.get("lon")
        if el_lat is None or el_lon is None:
            continue

        tags = element.get("tags", {})
        name = tags.get("name", "Unnamed Safe Location")

        # Categorize
        if tags.get("amenity") == "hospital":
            category = "hospitals"
        elif tags.get("amenity") == "shelter" or tags.get("building") == "bunker":
            category = "bunkers_shelters"
        elif tags.get("amenity") == "parking" and tags.get("parking") == "underground":
            category = "underground_parking"
        else:
            continue

        locations.append({
            "name": name,
            "lat": el_lat,
            "lon": el_lon,
            "category": category,
            "distance_km": haversine(lat, lon, el_lat, el_lon)
        })

    print(f"Found {len(locations)} safe locations from Overpass API")
    return locations


async def _get_fallback_locations(lat: float, lon: float, radius_km: float):
    """
    Provide fallback safe locations when Overpass API fails.
    These are generic safe locations that should exist in most urban areas.
    """
    print(f"Using fallback safe locations for {lat}, {lon}")

    # Create some reasonable fallback locations around the area
    fallback_locations = []

    # Add some hospitals in different directions
    hospital_offsets = [
        (0.01, 0.01, "City General Hospital"),
        (-0.01, 0.01, "Regional Medical Center"),
        (0.01, -0.01, "Emergency Hospital"),
        (-0.01, -0.01, "Community Health Center")
    ]

    for lat_offset, lon_offset, name in hospital_offsets:
        fallback_lat = lat + lat_offset
        fallback_lon = lon + lon_offset
        distance = haversine(lat, lon, fallback_lat, fallback_lon)

        if distance <= radius_km:
            fallback_locations.append({
                "name": name,
                "lat": fallback_lat,
                "lon": fallback_lon,
                "category": "hospitals",
                "distance_km": distance
            })

    # Add some shelters
    shelter_offsets = [
        (0.005, 0.005, "Emergency Shelter North"),
        (-0.005, 0.005, "Community Center Shelter"),
    ]

    for lat_offset, lon_offset, name in shelter_offsets:
        fallback_lat = lat + lat_offset
        fallback_lon = lon + lon_offset
        distance = haversine(lat, lon, fallback_lat, fallback_lon)

        if distance <= radius_km:
            fallback_locations.append({
                "name": name,
                "lat": fallback_lat,
                "lon": fallback_lon,
                "category": "bunkers_shelters",
                "distance_km": distance
            })

    print(f"Generated {len(fallback_locations)} fallback locations")
    return fallback_locations


async def get_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    """
    Get real road route using OSRM (Open Source Routing Machine).
    Returns distance, duration, and GeoJSON coordinates.
    """
    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)

        if response.status_code != 200:
            # If routing fails, calculate straight-line distance as fallback
            distance_km = haversine(start_lat, start_lon, end_lat, end_lon)
            return {
                "distance_m": distance_km * 1000,
                "duration_s": distance_km * 60,  # Assume 1km per minute
                "geometry": [[start_lon, start_lat], [end_lon, end_lat]]
            }

        route_data = response.json()

        if not route_data.get("routes"):
            # Fallback to straight line
            distance_km = haversine(start_lat, start_lon, end_lat, end_lon)
            return {
                "distance_m": distance_km * 1000,
                "duration_s": distance_km * 60,
                "geometry": [[start_lon, start_lat], [end_lon, end_lat]]
            }

        route = route_data["routes"][0]
        return {
            "distance_m": round(route["distance"], 1),
            "duration_s": round(route["duration"], 1),
            "geometry": route["geometry"]["coordinates"]  # [[lon, lat], ...]
        }

    except Exception as e:
        print(
            f"Routing failed for {start_lat},{start_lon} to {end_lat},{end_lon}: {e}")
        # Fallback to straight-line distance
        distance_km = haversine(start_lat, start_lon, end_lat, end_lon)
        return {
            "distance_m": distance_km * 1000,
            "duration_s": distance_km * 60,  # Assume 1km per minute
            "geometry": [[start_lon, start_lat], [end_lon, end_lat]]
        }


async def find_evacuation_routes(
    user_lat: float,
    user_lon: float,
    radius_km: float = 10.0,
    max_per_category: int = 2
):
    """
    Main logic: Find up to `max_per_category` nearest safe locations per category
    and compute real road routes to them.
    """
    print(
        f"Finding evacuation routes for {user_lat}, {user_lon} within {radius_km}km")

    safe_locations = await get_safe_locations(user_lat, user_lon, radius_km)

    # Sort by distance
    safe_locations.sort(key=lambda x: x["distance_km"])

    categories = {
        "hospitals": [],
        "bunkers_shelters": [],
        "underground_parking": []
    }

    for loc in safe_locations:
        category = loc["category"]
        if len(categories[category]) >= max_per_category:
            continue

        try:
            route = await get_route(user_lat, user_lon, loc["lat"], loc["lon"])

            categories[category].append({
                "safe_location": loc["name"],
                "lat": loc["lat"],
                "lon": loc["lon"],
                "google_maps": f"https://www.google.com/maps?q={loc['lat']},{loc['lon']}",
                "distance_km": round(loc["distance_km"], 2),
                "route": route
            })

            print(f"Added route to {loc['name']} ({category})")

        except Exception as e:
            print(f"Failed to get route to {loc['name']}: {e}")
            # Don't skip - routing now has fallbacks
            continue

    # Log final results
    for category, routes in categories.items():
        print(f"Final {category}: {len(routes)} routes")

    alert_id = str(uuid.uuid4())

    return {
        "alert_id": alert_id,
        "results": {
            "user_position": {"lat": user_lat, "lon": user_lon},
            "search_radius_km": radius_km,
            "routes": categories
        }
    }

# Initialize disaster response agent (will be set up in startup event)
disaster_response_agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize the disaster response agent on startup."""
    global disaster_response_agent
    try:
        # Import here to avoid circular imports
        from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
        from agentic_disaster_response.mcp_tools.tool_factory import create_default_tool_registry

        # Create MCP tool registry with default tools
        mcp_registry = create_default_tool_registry()

        # Initialize agent with configuration
        config = AgentConfiguration(
            context_search_radius_km=15.0,
            max_routes_per_category=3,
            enable_concurrent_processing=True,
            max_concurrent_disasters=3,
            enable_performance_monitoring=True
        )

            disaster_response_agent = DisasterResponseAgent(
                mcp_registry, config)

            # Initialize connections
            connection_results = await disaster_response_agent.initialize_connections()
            logger.info(
           f"Disaster Response Agent initialized with connections: {connection_results}")

            except Exception as e:
            logger.error(f"Failed to initialize Disaster Response Agent: {e}")
            # Continue without agent - evacuation routes will still work
            disaster_response_agent = None


@app.get("/")
                async def root():
    """Root endpoint with API information."""
    return {
        "message": "Evacuation System API",
        "version": "1.0.0",
        "endpoints": {
            "evacuation_routes": "/evacuation-routes",
            "trigger_disaster": "/disaster/trigger",
            "disaster_status": "/disaster/{disaster_id}/status",
            "system_health": "/system/health"
        }
    }


@ app.get("/health")
    async def health_check():
    """Health check endpoint."""
    return {
       "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "evacuation_system"
    }


@ app.post("/evacuation-routes", response_model=dict)
    async def get_evacuation_routes(request: EvacuationRequest):
    """
    Get evacuation routes for a given location.

    This is the original evacuation route functionality.
    """
    try:
    result = await find_evacuation_routes(
            user_lat=request.user_lat,
            user_lon=request.user_lon,
            radius_km=request.radius_km,
            max_per_category=request.max_per_category
        )
            return result
        except Exception as e:
        logger.error(f"Failed to find evacuation routes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to find evacuation routes: {str(e)}")


@ app.post("/disaster/trigger", response_model=DisasterEventResponse)
                async def trigger_disaster_event(request: DisasterEventRequest, background_tasks: BackgroundTasks):
    """
    Trigger a disaster event for autonomous processing.

    This endpoint integrates with the Disaster Response Agent to process
    disaster events autonomously through the complete workflow.
    """
    if disaster_response_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Disaster Response Agent is not available. Only evacuation routes are available."
        )

        try:
        # Generate unique disaster ID
        disaster_id = f"disaster_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # Create disaster data from request
        disaster_data = await _create_disaster_data_from_request(disaster_id, request)

        # Store disaster data for agent retrieval (in production, this would be in a database)
        await _store_disaster_data(disaster_id, disaster_data)

        # Start background processing
        background_tasks.add_task(_process_disaster_background, disaster_id)

        # Return immediate response
        response = DisasterEventResponse(
            disaster_id=disaster_id,
            status="processing_started",
            message=f"Disaster event {disaster_id} has been queued for autonomous processing",
            processing_started_at=datetime.now().isoformat(),
            estimated_completion_time=(
                datetime.now().replace(microsecond=0).isoformat() + "Z")
        )

            logger.info(f"Disaster event triggered: {disaster_id}")
            return response

        except Exception as e:
        logger.error(f"Failed to trigger disaster event: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger disaster event: {str(e)}")


@ app.get("/internal/disaster/{disaster_id}/data")
                async def get_internal_disaster_data(disaster_id: str):
    """
    Internal endpoint for the agent to retrieve disaster data.
    This ensures the agent gets data from the same store instance.
    """
    try:
        disaster_data = await _get_stored_disaster_data(disaster_id)

        if not disaster_data:
            raise HTTPException(
                status_code=404,
                detail=f"No disaster data found for ID: {disaster_id}"
            )

            # Convert DisasterData object to dictionary for JSON serialization
            return {
            "disaster_id": disaster_data.disaster_id,
            "disaster_type": disaster_data.disaster_type.value,
            "location": {
                "latitude": disaster_data.location.latitude,
                "longitude": disaster_data.location.longitude,
                "address": disaster_data.location.address,
                "administrative_area": disaster_data.location.administrative_area
            },
            "severity": disaster_data.severity.value,
            "timestamp": disaster_data.timestamp.isoformat(),
            "affected_areas": [
                {
                    "center": {
                        "latitude": area.center.latitude,
                        "longitude": area.center.longitude,
                        "address": area.center.address,
                        "administrative_area": area.center.administrative_area
                    },
                    "radius_km": area.radius_km,
                    "area_name": area.area_name
                }
                for area in disaster_data.affected_areas
            ],
            "estimated_impact": {
                "estimated_affected_population": disaster_data.estimated_impact.estimated_affected_population,
                "estimated_casualties": disaster_data.estimated_impact.estimated_casualties,
                "infrastructure_damage_level": disaster_data.estimated_impact.infrastructure_damage_level.value
            },
            "description": disaster_data.description,
            "source": disaster_data.source
        }

        except Exception as e:
        logger.error(
           f"Failed to retrieve internal disaster data for {disaster_id}: {e}")
            raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve disaster data: {str(e)}"
        )


@ app.get("/disaster/{disaster_id}/status")
        async def get_disaster_status(disaster_id: str):
        """
    Get the current status of a disaster processing operation.
    """
        if disaster_response_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Disaster Response Agent is not available"
        )

        try:
        # Get active disasters
        active_disasters = disaster_response_agent.get_active_disasters()

        if disaster_id in active_disasters:
        disaster_response = active_disasters[disaster_id]

            # Create status response
            status_response = {
               "disaster_id": disaster_id,
                "processing_status": disaster_response.processing_status,
                "start_time": disaster_response.start_time.isoformat(),
                "completion_time": disaster_response.completion_time.isoformat() if disaster_response.completion_time else None,
                "total_processing_time_seconds": disaster_response.total_processing_time_seconds,
                "error_count": len(disaster_response.errors),
                "has_critical_errors": disaster_response.has_critical_errors,
                "success_rate": disaster_response.success_rate
            }

                # Add context information if available
                if disaster_response.context:
            status_response["context"] = {
                   "context_completeness": disaster_response.context.context_completeness,
                    "affected_population": disaster_response.context.affected_population.total_population,
                    "evacuation_routes_count": len(disaster_response.context.evacuation_routes),
                    "missing_data_indicators": disaster_response.context.missing_data_indicators
                }

                # Add priority information if available
                if disaster_response.priority:
                status_response["priority"] = {
                   "level": disaster_response.priority.level.value,
                    "score": disaster_response.priority.score,
                    "confidence": disaster_response.priority.confidence,
                    "reasoning": disaster_response.priority.reasoning
                }

                # Add dispatch results summary
                if disaster_response.dispatch_results:
                successful_dispatches = sum(
                   1 for result in disaster_response.dispatch_results
                    if result.status.value == "success"
                )
                    status_response["dispatch_summary"] = {
                   "successful_dispatches": successful_dispatches,
                    "total_dispatch_attempts": len(disaster_response.dispatch_results),
                    "dispatch_results": [
                        {
                            "mcp_tool_name": result.mcp_tool_name,
                            "status": result.status.value,
                            "recipients_count": result.recipients_count,
                            "successful_deliveries": result.successful_deliveries,
                            "failed_deliveries": result.failed_deliveries,
                            "error_message": result.error_message,
                            "execution_time_seconds": result.execution_time_seconds
                        }
                        for result in disaster_response.dispatch_results
                    ]
                }

                # Add error details if present
                if disaster_response.errors:
                status_response["errors"] = [
                   {
                        "component": error.component,
                        "severity": error.severity.value,
                        "error_type": error.error_type,
                        "error_message": error.error_message,
                        "timestamp": error.timestamp.isoformat(),
                        "recovery_action_taken": error.recovery_action_taken,
                        "resolved": error.resolved
                    }
                    for error in disaster_response.errors
                ]

                return status_response
                else:
                # Check if disaster exists in stored data but not in active processing
                stored_data = await _get_stored_disaster_data(disaster_id)
                if stored_data:
                return {
                   "disaster_id": disaster_id,
                    "processing_status": "completed_or_not_started",
                    "message": "Disaster data exists but is not currently being processed"
                }
                else:
                raise HTTPException(
                    status_code=404, detail=f"Disaster {disaster_id} not found")

                    except HTTPException:
                    raise
                    except Exception as e:
                    logger.error(
                        f"Failed to get disaster status for {disaster_id}: {e}")
                    raise HTTPException(
            status_code=500, detail=f"Failed to get disaster status: {str(e)}")


@ app.get("/system/health")
                async def get_system_health():
    """
    Get system health status including disaster response agent status.
    """
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "evacuation_system": "healthy",
        "disaster_response_agent": "unavailable"
    }

        try:
        # Test evacuation system
    test_result = await find_evacuation_routes(52.5200, 13.4050, 5.0, 1)
        if test_result and "alert_id" in test_result:
    health_status["evacuation_system"] = "healthy"
        else:
    health_status["evacuation_system"] = "degraded"
        except Exception as e:
    health_status["evacuation_system"] = "unhealthy"
        health_status["evacuation_system_error"] = str(e)

        # Test disaster response agent
        if disaster_response_agent is not None:
    try:
    agent_health = await disaster_response_agent.monitor_system_health()
            health_status["disaster_response_agent"] = agent_health["overall_health"]
            health_status["agent_details"] = {
               "component_status": agent_health["component_status"],
                "active_disasters": agent_health["active_disasters"],
                "recovery_actions": agent_health.get("recovery_actions", [])
            }
            except Exception as e:
            health_status["disaster_response_agent"] = "unhealthy"
            health_status["agent_error"] = str(e)

            return health_status


@ app.get("/system/status")
                async def get_system_status():
    """
    Get comprehensive system status including real-time metrics.
    """
    if disaster_response_agent is None:
        return {
            "timestamp": datetime.now().isoformat(),
            "disaster_response_agent": "unavailable",
            "evacuation_system": "available",
            "message": "Only evacuation route functionality is available"
        }

        try:
        # Get real-time status from agent
        real_time_status = await disaster_response_agent.get_real_time_status()

        # Add evacuation system status
        real_time_status["evacuation_system"] = {
           "status": "healthy",
            "endpoints_available": [
                "/evacuation-routes",
                "/disaster/trigger",
                "/disaster/{disaster_id}/status"
            ]
        }

            return real_time_status

        except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
           "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "evacuation_system": "available",
            "disaster_response_agent": "error"
        }


        # Helper functions for disaster data management
        async def _create_disaster_data_from_request(disaster_id: str, request: DisasterEventRequest):
        """Create DisasterData object from API request."""
        from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel, GeographicalArea, ImpactAssessment
        from agentic_disaster_response.models.location import Location

        # Map string values to enums
        disaster_type_mapping = {
        "fire": DisasterType.FIRE,
        "flood": DisasterType.FLOOD,
        "earthquake": DisasterType.EARTHQUAKE,
        "tornado": DisasterType.TORNADO,
        "chemical_spill": DisasterType.CHEMICAL_SPILL,
        "explosion": DisasterType.EXPLOSION,
        "building_collapse": DisasterType.BUILDING_COLLAPSE,
        "terrorist_attack": DisasterType.TERRORIST_ATTACK,
        "volcanic": DisasterType.VOLCANIC,
        "electrical": DisasterType.ELECTRICAL
    }

        severity_mapping = {
       "low": SeverityLevel.LOW,
        "medium": SeverityLevel.MEDIUM,
        "high": SeverityLevel.HIGH,
        "critical": SeverityLevel.CRITICAL
    }

        # Create location
        location = Location(
        latitude=request.location_lat,
        longitude=request.location_lon,
        address=f"Disaster location at {request.location_lat:.4f}, {request.location_lon:.4f}",
        administrative_area="emergency_zone"
    )

        # Create affected area
        affected_area = GeographicalArea(
        center=location,
        radius_km=request.affected_radius_km,
        area_name=f"Affected area for {disaster_id}"
    )

        # Create impact assessment
        impact = ImpactAssessment(
        estimated_affected_population=request.estimated_affected_population or 1000,
        estimated_casualties=max(
            1, int((request.estimated_affected_population or 1000) * 0.01)),
        infrastructure_damage_level=severity_mapping.get(
            request.severity.lower(), SeverityLevel.MEDIUM)
    )

        # Create disaster data
        disaster_data = DisasterData(
        disaster_id=disaster_id,
        disaster_type=disaster_type_mapping.get(
            request.disaster_type.lower(), DisasterType.FIRE),
        location=location,
        severity=severity_mapping.get(
            request.severity.lower(), SeverityLevel.MEDIUM),
        timestamp=datetime.now(),
        affected_areas=[affected_area],
        estimated_impact=impact,
        description=request.description or f"{request.disaster_type} disaster at {location.address}",
        source="fastapi_backend"
    )

        return disaster_data


    # In-memory storage for disaster data (in production, use a database)
    _disaster_data_store: Dict[str, Any] = {}


    async def _store_disaster_data(disaster_id: str, disaster_data):
    """Store disaster data for agent retrieval."""
    _disaster_data_store[disaster_id] = disaster_data
    logger.info(f"Stored disaster data for {disaster_id}")
    logger.info(f"Data type: {type(disaster_data)}")
    logger.info(f"Store now contains {len(_disaster_data_store)} items")
    logger.info(f"Store keys: {list(_disaster_data_store.keys())}")


    async def _get_stored_disaster_data(disaster_id: str):
    """Retrieve stored disaster data."""
    logger.info(f"Looking for disaster data with ID: {disaster_id}")
    logger.info(
       f"Current disaster store keys: {list(_disaster_data_store.keys())}")
        logger.info(f"Store size: {len(_disaster_data_store)}")

        data = _disaster_data_store.get(disaster_id)
        if data:
        logger.info(f"Found disaster data for {disaster_id}: {type(data)}")
        else:
        logger.warning(f"No disaster data found for {disaster_id}")

        return data


        async def _process_disaster_background(disaster_id: str):
        """Background task to process disaster through the agent."""
        if disaster_response_agent is None:
        logger.error(
           f"Cannot process disaster {disaster_id}: agent not available")
            return

            try:
            logger.info(
            f"Starting background processing for disaster {disaster_id}")

            # Process the disaster event
            disaster_response = await disaster_response_agent.process_disaster_event(disaster_id)

            logger.info(
            f"Completed processing for disaster {disaster_id}: status={disaster_response.processing_status}")

            # In production, you might want to store the results or send notifications

            except Exception as e:
            logger.error(
            f"Background processing failed for disaster {disaster_id}: {e}")


            # Update the get_disaster_data function to use stored data
            async def get_disaster_data(disaster_id: str):
            """
    Retrieve disaster data from storage.
    This function is used by the DisasterResponseAgent.
    """
            stored_data = await _get_stored_disaster_data(disaster_id)
            if stored_data:
            return stored_data

            # If not found in storage, this would query the actual backend in production
            raise Exception(f"Disaster data not found for ID: {disaster_id}")


            # Keep the original functions for backward compatibility


            # Example usage when running the file directly
            if __name__ == "__main__":
            async def main():
            # Example: Near central Berlin
            result = await find_evacuation_routes(
            user_lat=52.5200,
            user_lon=13.4050,
            radius_km=15.0
        )
            print(result)

        asyncio.run(main())
