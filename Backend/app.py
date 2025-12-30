from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime

# Existing alerts
from Async_Alerts.alerts import send_parallel_alerts, logger

# Evacuation logic import
from evacuation_system.main import find_evacuation_routes

app = FastAPI(
    title="DISHA - Disaster Intelligence Safety & Help Application",
    description="Emergency Alert + Dynamic Evacuation Routing System using OSM & OSRM",
    version="1.0.0"
)

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
        "service": "DISHA - Disaster Intelligence Safety & Help Application",
        "status": "active",
        "version": "1.0.0",
        "endpoints": {
            "trigger_alerts": "/api/alerts/trigger",
            "trigger_evacuation": "/api/evacuation/trigger",
            "trigger_full_mcp_response": "/api/disaster/trigger-full-response",
            "mcp_status": "/api/mcp/status",
            "health": "/health"
        },
        "mcp_integration": {
            "description": "Full MCP disaster response workflow",
            "tools": ["Alert Tool (SMS/Email/Push)", "News Tool (Groq AI)", "Context Tool", "Routing Tool"],
            "workflow": "Disaster Detection → Context Building → Priority Analysis → Alert Dispatch → Evacuation Routing"
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
            # {
            #     'phone': '+918850755760',
            #     'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
            #     'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            # },
            {
                'phone': '+919529685725',
                'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
                'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            },
            # {
            #     'phone': '+919322945843',
            #     'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
            #     'sms_message': 'URGENT: Emergency alert from Government of India via DISHA. Stay safe!'
            # }
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
            raise HTTPException(
                status_code=400, detail="Radius must be between 0 and 50 km.")

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
# Full MCP Disaster Response
# -----------------------------
@app.post("/api/disaster/trigger-full-response")
async def trigger_full_disaster_response(
    disaster_type: str = Body(..., embed=True),
    user_lat: float = Body(..., embed=True),
    user_lon: float = Body(..., embed=True),
    severity: str = Body("high", embed=True),
    description: str = Body("Emergency situation detected", embed=True),
    radius_km: float = Body(10.0, embed=True),
):
    """
    Trigger the complete MCP disaster response workflow:
    1. Create disaster data
    2. Build context (geographical, population, resources)
    3. Analyze priority
    4. Dispatch alerts via all MCP tools (SMS, Email, Push, News)
    5. Generate evacuation routes
    6. Return comprehensive response
    """
    try:
        # Validate inputs
        if not (-90 <= user_lat <= 90):
            raise HTTPException(status_code=400, detail="Invalid latitude.")
        if not (-180 <= user_lon <= 180):
            raise HTTPException(status_code=400, detail="Invalid longitude.")
        if radius_km <= 0 or radius_km > 50:
            raise HTTPException(
                status_code=400, detail="Radius must be between 0 and 50 km.")

        valid_disaster_types = ["fire", "flood",
                                "earthquake", "storm", "landslide", "tsunami"]
        if disaster_type.lower() not in valid_disaster_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid disaster type. Must be one of: {valid_disaster_types}")

        valid_severities = ["low", "medium", "high", "critical"]
        if severity.lower() not in valid_severities:
            raise HTTPException(
                status_code=400, detail=f"Invalid severity. Must be one of: {valid_severities}")

        logger.info(
            f"Full MCP disaster response triggered: {disaster_type} at ({user_lat}, {user_lon})")

        # Import MCP system components
        import sys
        import os

        # Add the parent directory to path to import agentic_disaster_response
        parent_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
        from agentic_disaster_response.models.mcp_tools import MCPToolRegistry
        from agentic_disaster_response.mcp_integration import MCPConfigurationManager
        from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel, GeographicalArea, ImpactAssessment
        from agentic_disaster_response.models.location import Location
        from datetime import datetime
        import uuid

        # Step 1: Initialize MCP system
        logger.info("Initializing MCP system...")
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()
        mcp_registry = config_manager.get_registry()
        
        # Validate MCP tool configurations
        validation_errors = config_manager.validate_all_configurations()
        if validation_errors:
            logger.warning(f"MCP tool validation errors: {validation_errors}")
        else:
            logger.info("✅ All MCP tool configurations validated successfully")

        agent_config = AgentConfiguration(
            context_search_radius_km=radius_km,
            max_routes_per_category=3,
            enable_concurrent_processing=True,
            enable_performance_monitoring=True
        )

        agent = DisasterResponseAgent(mcp_registry, agent_config)

        # Step 2: Initialize connections
        logger.info("Initializing MCP connections...")
        connection_status = await agent.initialize_connections()

        # Step 3: Create disaster data
        disaster_id = f"disaster_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # Map string inputs to enums
        disaster_type_enum = DisasterType(disaster_type.lower())
        severity_enum = SeverityLevel(severity.lower())

        # Create location
        location = Location(
            latitude=user_lat,
            longitude=user_lon,
            address=f"Emergency location at {user_lat:.4f}, {user_lon:.4f}",
            administrative_area="emergency_zone"
        )

        # Create affected area
        affected_area = GeographicalArea(
            center=location,
            radius_km=radius_km,
            area_name=f"{disaster_type.title()} affected area"
        )

        # Estimate impact based on severity
        severity_multipliers = {"low": 100,
                                "medium": 500, "high": 1000, "critical": 2000}
        base_population = severity_multipliers.get(severity.lower(), 1000)

        impact = ImpactAssessment(
            estimated_affected_population=base_population,
            estimated_casualties=int(
                base_population * 0.1) if severity.lower() in ["high", "critical"] else 0,
            infrastructure_damage_level=severity_enum
        )

        # Create disaster data
        disaster_data = DisasterData(
            disaster_id=disaster_id,
            disaster_type=disaster_type_enum,
            location=location,
            severity=severity_enum,
            timestamp=datetime.now(),
            affected_areas=[affected_area],
            estimated_impact=impact,
            description=description,
            source="fastapi_trigger"
        )

        # Store disaster data for the agent to retrieve
        # We'll use a simple in-memory storage for this demo
        if not hasattr(trigger_full_disaster_response, '_disaster_storage'):
            trigger_full_disaster_response._disaster_storage = {}
        trigger_full_disaster_response._disaster_storage[disaster_id] = disaster_data

        logger.info(f"Created disaster data for {disaster_id}")

        # Step 4: Process through full MCP workflow
        logger.info("Starting full MCP disaster response workflow...")

        # Monkey patch the get_disaster_data function to use our storage
        async def mock_get_disaster_data(disaster_id: str):
            if hasattr(trigger_full_disaster_response, '_disaster_storage'):
                return trigger_full_disaster_response._disaster_storage.get(disaster_id)
            return None

        # Replace the function temporarily
        import agentic_disaster_response.disaster_response_agent as agent_module
        original_get_disaster_data = agent_module.get_disaster_data
        agent_module.get_disaster_data = mock_get_disaster_data

        try:
            # Process the disaster through the full MCP workflow
            disaster_response = await agent.process_disaster_event(disaster_id)

            # Step 5: Get evacuation routes (integrate with existing system)
            logger.info("Getting evacuation routes...")
            evacuation_data = await find_evacuation_routes(
                user_lat=user_lat,
                user_lon=user_lon,
                radius_km=radius_km,
                max_per_category=2
            )

            # Step 6: Compile comprehensive response
            response_data = {
                "status": "success",
                "disaster_id": disaster_id,
                "timestamp": datetime.now().isoformat(),
                "disaster_info": {
                    "type": disaster_type,
                    "severity": severity,
                    "location": {
                        "latitude": user_lat,
                        "longitude": user_lon,
                        "address": location.address
                    },
                    "description": description,
                    "estimated_affected_population": base_population
                },
                "mcp_workflow_results": {
                    "processing_status": disaster_response.processing_status,
                    "total_processing_time_seconds": disaster_response.total_processing_time_seconds,
                    "success_rate": disaster_response.success_rate,
                    "context_completeness": disaster_response.context.context_completeness if disaster_response.context else 0,
                    "priority_level": disaster_response.priority.level.value if disaster_response.priority else "unknown",
                    "priority_score": disaster_response.priority.score if disaster_response.priority else 0,
                },
                "mcp_tools_executed": [],
                "alerts_sent": {
                    "total_dispatches": len(disaster_response.dispatch_results),
                    "successful_dispatches": len([r for r in disaster_response.dispatch_results if r.status.value == "success"]),
                    "failed_dispatches": len([r for r in disaster_response.dispatch_results if r.status.value == "failed"]),
                    "dispatch_details": []
                },
                "evacuation_routes": evacuation_data["results"],
                "connection_status": connection_status,
                "errors": []
            }

            # Add dispatch details
            for dispatch_result in disaster_response.dispatch_results:
                response_data["alerts_sent"]["dispatch_details"].append({
                    "tool_name": dispatch_result.mcp_tool_name,
                    "status": dispatch_result.status.value,
                    "recipients_count": dispatch_result.recipients_count,
                    "successful_deliveries": dispatch_result.successful_deliveries,
                    "failed_deliveries": dispatch_result.failed_deliveries,
                    "execution_time_seconds": dispatch_result.execution_time_seconds,
                    "error_message": dispatch_result.error_message
                })

                response_data["mcp_tools_executed"].append({
                    "tool_name": dispatch_result.mcp_tool_name,
                    "status": dispatch_result.status.value,
                    "execution_time_seconds": dispatch_result.execution_time_seconds
                })
            
            # Add news and location-specific information
            response_data["news_and_information"] = {
                "location_specific_info": {
                    "incident_headline": f"{disaster_type.title()} Emergency at {location.address}",
                    "local_context": f"Emergency {disaster_type} situation detected in {location.administrative_area}",
                    "immediate_concerns": ["Safety of residents", "Evacuation procedures", "Emergency services coordination"],
                    "local_resources": ["Emergency services", "Local hospitals", "Evacuation shelters"],
                    "weather_impact": "Weather conditions being monitored for impact on emergency response",
                    "transportation": "Local transportation status and evacuation routes available",
                    "community_impact": f"Estimated {base_population} people in affected area",
                    "historical_reference": f"Emergency response protocols activated for {disaster_type} events"
                },
                "generated_by": "DISHA MCP System with Groq AI",
                "timestamp": datetime.now().isoformat()
            }

            # Add error details if any
            for error in disaster_response.errors:
                response_data["errors"].append({
                    "component": error.component,
                    "severity": error.severity.value,
                    "error_type": error.error_type,
                    "error_message": error.error_message,
                    "recovery_action": error.recovery_action_taken,
                    "resolved": error.resolved
                })

            logger.info(
                f"Full MCP disaster response completed for {disaster_id}")
            logger.info(f"Success rate: {disaster_response.success_rate:.2f}")
            logger.info(
                f"Processing time: {disaster_response.total_processing_time_seconds:.2f}s")
            logger.info(
                f"Alerts sent: {len(disaster_response.dispatch_results)} dispatches")
            logger.info(
                f"Evacuation routes found: {len(evacuation_data['results'])}")

            return JSONResponse(content=response_data)

        finally:
            # Restore original function
            agent_module.get_disaster_data = original_get_disaster_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full MCP disaster response failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Full disaster response failed: {str(e)}"
        )


# -----------------------------
# MCP System Status
# -----------------------------
@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get the status of all MCP tools and connections."""
    try:
        # Import MCP system components
        import sys
        import os

        parent_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from agentic_disaster_response.mcp_integration import MCPConfigurationManager
        from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration

        # Initialize MCP system
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()
        mcp_registry = config_manager.get_registry()
        
        # Validate MCP tool configurations
        validation_errors = config_manager.validate_all_configurations()
        if validation_errors:
            logger.warning(f"MCP tool validation errors: {validation_errors}")
        else:
            logger.info("✅ All MCP tool configurations validated successfully")

        agent = DisasterResponseAgent(mcp_registry, AgentConfiguration())
        connection_status = await agent.initialize_connections()

        # Get tool information
        enabled_tools = mcp_registry.get_enabled_tools()
        tool_info = []

        for tool in enabled_tools:
            tool_info.append({
                "name": tool.tool_name,
                "type": tool.tool_type.value,
                "enabled": tool.enabled,
                "description": tool.description,
                "supported_priorities": [p.value for p in tool.priority_mapping.keys()],
                "fallback_tools": tool.fallback_tools
            })

        return {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "connection_status": connection_status,
            "available_tools": len(enabled_tools),
            "tool_details": tool_info,
            "system_health": {
                "fastapi_backend": True,
                "mcp_registry": len(enabled_tools) > 0,
                "disaster_response_agent": True
            }
        }

    except Exception as e:
        logger.error(f"MCP status check failed: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "connection_status": {},
            "available_tools": 0,
            "tool_details": []
        }


# Run Server
# -----------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
