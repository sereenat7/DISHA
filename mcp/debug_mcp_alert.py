#!/usr/bin/env python3
"""
Debug script to test MCP alert system initialization and execution.
"""

from datetime import datetime, timedelta
import logging
import asyncio
import sys
import os
sys.path.append('.')
sys.path.append('./Backend')


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(message)s')


async def test_mcp_alert_system():
    """Test MCP alert system initialization and basic functionality."""

    try:
        print("🔍 Testing MCP Alert System...")

        # Import required modules
        from agentic_disaster_response.mcp_tools.alert_tool import AlertMCPTool
        from agentic_disaster_response.models.mcp_tools import MCPToolConfig, MCPToolType, ToolConfiguration
        from agentic_disaster_response.models.alert_priority import PriorityLevel, AlertPriority
        from agentic_disaster_response.models.context import StructuredContext
        from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
        from agentic_disaster_response.models.location import Location
        from agentic_disaster_response.mcp_integration import AlertData

        print("✅ All imports successful")

        # Create tool config
        config = MCPToolConfig(
            tool_name='debug_alert_tool',
            tool_type=MCPToolType.ALERT,
            priority_mapping={
                PriorityLevel.HIGH: ToolConfiguration(
                    endpoint='debug://alert',
                    timeout_seconds=30,
                    max_retries=1,
                    parameters={
                        'channels': ['sms', 'email'],
                        'broadcast_radius_km': 10
                    }
                )
            }
        )

        # Initialize tool
        print("🔧 Initializing AlertMCPTool...")
        tool = AlertMCPTool(config)
        print("✅ AlertMCPTool initialized successfully")

        # Check service status
        print("\n📊 Service Status:")
        print(
            f"  Twilio client: {'✅ Available' if tool.twilio_client is not None else '❌ Not available'}")
        print(
            f"  SendGrid client: {'✅ Available' if tool.sendgrid_client is not None else '❌ Not available'}")
        print(
            f"  Firebase initialized: {'✅ Available' if tool.firebase_initialized else '❌ Not available'}")

        # Create minimal test data
        print("\n🏗️ Creating test alert data...")

        location = Location(
            latitude=19.0176,
            longitude=72.8562,
            address="Mumbai, Maharashtra, India",
            administrative_area="Mumbai"
        )

        disaster_data = DisasterData(
            disaster_id="debug_test_001",
            disaster_type=DisasterType.FLOOD,
            location=location,
            severity=SeverityLevel.HIGH,
            timestamp=datetime.now(),
            affected_areas=[location],
            estimated_impact=None,
            description="Debug test flood",
            source="debug_script"
        )

        # Create minimal structured context
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
            score=0.7,
            confidence=0.8,
            reasoning="Debug test alert",
            estimated_response_time=timedelta(minutes=30),
            required_resources=[]
        )

        # Create alert data
        alert_data = AlertData(
            alert_id="debug_alert_001",
            priority=alert_priority,
            context=structured_context,
            message="🚨 DEBUG TEST: Emergency flood alert for Mumbai area. This is a test of the MCP alert system.",
            recipients=["+918850755760", "+919529685725"],
            channels=["sms", "email"],
            metadata={"test": True, "debug": True}
        )

        print("✅ Test alert data created")

        # Get tool configuration
        tool_configuration = config.get_config_for_priority(PriorityLevel.HIGH)

        # Execute the alert tool
        print("\n🚀 Executing alert tool...")
        result = await tool.execute(alert_data, tool_configuration)

        print(f"\n📊 Execution Result:")
        print(f"  Status: {result.status.value}")
        print(f"  Tool Name: {result.tool_name}")
        print(f"  Execution Time: {result.execution_time_ms}ms")

        if result.response_data:
            print(f"  Response Data:")
            for key, value in result.response_data.items():
                if key == 'delivery_results':
                    print(f"    {key}: {len(value)} delivery attempts")
                    for delivery in value:
                        status_icon = "✅" if delivery.get('success') else "❌"
                        print(
                            f"      {status_icon} {delivery.get('channel', 'unknown')}: {delivery.get('success', False)}")
                else:
                    print(f"    {key}: {value}")

        if result.error_message:
            print(f"  Error: {result.error_message}")

        # Close the tool
        await tool.__aexit__(None, None, None)

        return result.status.value == 'success'

    except Exception as e:
        print(f"❌ Error during MCP alert test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_alert_system())
    if success:
        print("\n🎉 MCP Alert System test completed successfully!")
    else:
        print("\n❌ MCP Alert System test failed!")
