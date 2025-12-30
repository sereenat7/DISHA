#!/usr/bin/env python3
"""
Test script to verify MCP tools are using real services.
"""

from agentic_disaster_response.mcp_integration import AlertData
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
from agentic_disaster_response.models.context import StructuredContext
from agentic_disaster_response.models.alert_priority import AlertPriority, PriorityLevel
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, ToolConfiguration, MCPToolType
from agentic_disaster_response.mcp_tools.news_tool import NewsMCPTool
from agentic_disaster_response.mcp_tools.alert_tool import AlertMCPTool
import asyncio
import logging
import os
from datetime import datetime, timedelta

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_real_services():
    """Test that MCP tools are using real services."""

    print("🔧 Testing MCP Tools Real Service Integration")
    print("=" * 60)

    # Create test location (Mumbai)
    location = Location(
        latitude=19.0176,
        longitude=72.8562,
        address="Mumbai, Maharashtra, India",
        administrative_area="Maharashtra"
    )

    # Create test disaster data
    disaster_data = DisasterData(
        disaster_id="test_real_services_001",
        disaster_type=DisasterType.FLOOD,
        location=location,
        severity=SeverityLevel.HIGH,
        timestamp=datetime.now(),
        affected_areas=[location],
        estimated_impact=None,
        description="Test flood for real service verification",
        source="test_script"
    )

    # Create minimal context
    from agentic_disaster_response.models.context import (
        GeographicalContext, PopulationData, ResourceInventory, RiskMetrics
    )

    geographical_context = GeographicalContext(
        affected_areas=[location],
        safe_locations=[],
        blocked_routes=[],
        accessible_routes=[]
    )

    population_data = PopulationData(
        total_population=1000,
        vulnerable_population=200,
        current_occupancy=1000,
        population_density_per_km2=100.0
    )

    resource_inventory = ResourceInventory(
        available_shelters=1,
        shelter_capacity=100,
        medical_facilities=1,
        emergency_vehicles=1,
        communication_systems=1,
        backup_power_systems=1
    )

    risk_metrics = RiskMetrics(
        overall_risk_score=0.7,
        evacuation_difficulty=0.5,
        time_criticality=0.6,
        resource_availability=0.4,
        weather_impact=0.3,
        traffic_congestion=0.4
    )

    structured_context = StructuredContext(
        disaster_info=disaster_data,
        geographical_context=geographical_context,
        evacuation_routes=[],
        affected_population=population_data,
        available_resources=resource_inventory,
        risk_assessment=risk_metrics,
        context_completeness=0.6,
        missing_data_indicators=[]
    )

    # Create alert priority
    alert_priority = AlertPriority(
        level=PriorityLevel.HIGH,
        score=0.8,
        confidence=0.9,
        reasoning="Test alert for real service verification",
        estimated_response_time=timedelta(minutes=15),
        required_resources=[]
    )

    # Create alert data
    alert_data = AlertData(
        alert_id="test_real_services_001",
        priority=alert_priority,
        context=structured_context,
        message="🚨 TEST ALERT: This is a test of real notification services. Please ignore.",
        recipients=[],
        channels=[],
        metadata={"test": True}
    )

    # Test Alert Tool
    print("\n📱 Testing Alert Tool Real Services...")
    print("-" * 40)

    alert_config = MCPToolConfig(
        tool_name="test_alert_tool",
        tool_type=MCPToolType.ALERT,
        description="Test alert tool",
        priority_mapping={
            PriorityLevel.HIGH: ToolConfiguration(
                endpoint="local",
                timeout_seconds=30,
                max_retries=2,
                parameters={
                    "channels": ["sms", "email", "mobile_push"],
                    "broadcast_radius_km": 10
                }
            )
        }
    )

    alert_tool = AlertMCPTool(alert_config)

    # Check service initialization
    print(
        f"Twilio Client: {'✅ REAL' if alert_tool.twilio_client else '❌ SIMULATION'}")
    print(
        f"SendGrid Client: {'✅ REAL' if alert_tool.sendgrid_client else '❌ SIMULATION'}")
    print(
        f"Firebase Client: {'✅ REAL' if alert_tool.firebase_initialized else '❌ SIMULATION'}")

    # Execute alert tool
    tool_config = alert_config.get_config_for_priority(PriorityLevel.HIGH)
    alert_result = await alert_tool.execute(alert_data, tool_config)

    print(f"\nAlert Tool Result:")
    print(f"  Status: {alert_result.status.value}")
    print(f"  Execution Time: {alert_result.execution_time_ms}ms")
    if alert_result.response_data:
        real_services = alert_result.response_data.get(
            "real_services_used", {})
        print(f"  Real Services Used:")
        print(f"    Twilio: {'✅' if real_services.get('twilio') else '❌'}")
        print(f"    SendGrid: {'✅' if real_services.get('sendgrid') else '❌'}")
        print(f"    Firebase: {'✅' if real_services.get('firebase') else '❌'}")

        delivery_results = alert_result.response_data.get(
            "delivery_results", [])
        for result in delivery_results:
            service = result.get("service", "unknown")
            channel = result.get("channel", "unknown")
            success = result.get("success", False)
            print(f"    {channel}: {'✅' if success else '❌'} ({service})")

    # Test News Tool
    print("\n📰 Testing News Tool Real Services...")
    print("-" * 40)

    news_config = MCPToolConfig(
        tool_name="test_news_tool",
        tool_type=MCPToolType.NEWS,
        description="Test news tool",
        priority_mapping={
            PriorityLevel.HIGH: ToolConfiguration(
                endpoint="local",
                timeout_seconds=30,
                max_retries=2,
                parameters={
                    "operations": ["current_disasters", "emergency_bulletin"]
                }
            )
        }
    )

    news_tool = NewsMCPTool(news_config)

    # Check service initialization
    print(
        f"Groq Client: {'✅ REAL' if news_tool.groq_client else '❌ SIMULATION'}")

    # Execute news tool
    news_tool_config = news_config.get_config_for_priority(PriorityLevel.HIGH)
    news_result = await news_tool.execute(alert_data, news_tool_config)

    print(f"\nNews Tool Result:")
    print(f"  Status: {news_result.status.value}")
    print(f"  Execution Time: {news_result.execution_time_ms}ms")
    if news_result.response_data:
        groq_used = news_result.response_data.get("groq_service_used", False)
        print(f"  Groq Service Used: {'✅' if groq_used else '❌'}")

        results = news_result.response_data.get("results", {})
        for operation, result in results.items():
            service = result.get("service", "unknown")
            success = result.get("success", False)
            print(f"    {operation}: {'✅' if success else '❌'} ({service})")

    print("\n" + "=" * 60)
    print("🎯 Real Service Integration Test Complete!")

    # Summary
    real_services_working = []
    if alert_tool.twilio_client:
        real_services_working.append("Twilio SMS/Voice")
    if alert_tool.sendgrid_client:
        real_services_working.append("SendGrid Email")
    if alert_tool.firebase_initialized:
        real_services_working.append("Firebase Push")
    if news_tool.groq_client:
        real_services_working.append("Groq AI News")

    if real_services_working:
        print(f"✅ Real services working: {', '.join(real_services_working)}")
    else:
        print("❌ No real services are working - all using simulation")

    return len(real_services_working) > 0


if __name__ == "__main__":
    success = asyncio.run(test_real_services())
    exit(0 if success else 1)
