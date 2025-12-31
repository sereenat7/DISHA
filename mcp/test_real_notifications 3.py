#!/usr/bin/env python3
"""
Test script for real notification integrations.
Tests Twilio SMS, SendGrid Email, Firebase Push, and Groq News.
"""

from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel, GeographicalArea, ImpactAssessment
from agentic_disaster_response.models.location import Location
from agentic_disaster_response.models.context import EvacuationRoute, PopulationData, ResourceInventory, RiskMetrics, GeographicalContext
from agentic_disaster_response.models.alert_priority import AlertPriority
from agentic_disaster_response.models.context import StructuredContext
from agentic_disaster_response.mcp_integration import AlertData
from agentic_disaster_response.models.alert_priority import PriorityLevel
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, MCPToolType, ToolConfiguration
from agentic_disaster_response.mcp_tools.news_tool import NewsMCPTool
from agentic_disaster_response.mcp_tools.alert_tool import AlertMCPTool
import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_real_notifications():
    """Test real notification services."""
    print("🚀 Testing Real Notification Services")
    print("=" * 50)

    # Create test disaster context
    location = Location(
        latitude=19.0760,
        longitude=72.8777,
        address="Mumbai, Maharashtra, India",
        administrative_area="Mumbai"
    )

    disaster_info = DisasterData(
        disaster_id="test_real_notifications",
        disaster_type=DisasterType.FLOOD,
        location=location,
        severity=SeverityLevel.HIGH,
        timestamp=datetime.now(),
        affected_areas=[GeographicalArea(
            center=location,
            radius_km=5.0,
            area_name="Mumbai Central"
        )],
        estimated_impact=ImpactAssessment(
            estimated_affected_population=5000,
            infrastructure_damage_level=SeverityLevel.HIGH
        ),
        description="Test flood for real notification system"
    )

    affected_population = PopulationData(
        total_population=5000,
        vulnerable_population=1200
    )

    context = StructuredContext(
        disaster_info=disaster_info,
        affected_population=affected_population,
        evacuation_routes=[],
        geographical_context=GeographicalContext(
            affected_areas=[location],
            safe_locations=[]
        ),
        available_resources=ResourceInventory(
            available_shelters=3,
            shelter_capacity=2000,
            medical_facilities=2,
            emergency_vehicles=5,
            communication_systems=3,
            backup_power_systems=2
        ),
        risk_assessment=RiskMetrics(
            overall_risk_score=0.8,
            evacuation_difficulty=0.7,
            time_criticality=0.9,
            resource_availability=0.6
        ),
        context_completeness=0.85,
        missing_data_indicators=[]
    )

    priority = AlertPriority(
        level=PriorityLevel.HIGH,
        score=0.85,
        reasoning="High severity flood in densely populated area requiring immediate evacuation",
        estimated_response_time=timedelta(minutes=30),
        required_resources=[],
        confidence=0.9
    )

    alert_data = AlertData(
        alert_id="test_real_notifications",
        priority=priority,
        context=context,
        message="URGENT: Flood alert in Mumbai. Immediate evacuation required for low-lying areas. Follow official evacuation routes.",
        recipients=["+918850755760", "+919529685725", "+919322945843"],
        channels=["sms", "email", "mobile_push"],
        metadata={"test": True}
    )

    # Test Alert Tool (Real SMS/Email/Push)
    print("\n📱 Testing Real Alert Tool (SMS, Email, Push)")
    print("-" * 40)

    alert_config = MCPToolConfig(
        tool_name="test_alert_tool",
        tool_type=MCPToolType.ALERT,
        priority_mapping={
            PriorityLevel.HIGH: ToolConfiguration(
                endpoint="mcp://alert/high",
                timeout_seconds=60,
                max_retries=2,
                parameters={
                    "channels": ["sms", "email", "mobile_push"],
                    "broadcast_radius_km": 10
                }
            )
        },
        fallback_tools=[],
        description="Test alert tool for real services"
    )

    alert_tool = AlertMCPTool(alert_config)

    try:
        alert_result = await alert_tool.execute(alert_data, alert_config.priority_mapping[PriorityLevel.HIGH])
        print(f"✅ Alert Tool Result: {alert_result.status.value}")
        if alert_result.response_data:
            print(
                f"   Channels attempted: {alert_result.response_data.get('channels_attempted', 0)}")
            print(
                f"   Successful deliveries: {alert_result.response_data.get('successful_deliveries', 0)}")
            print(f"   Real services used:")
            services = alert_result.response_data.get('real_services_used', {})
            for service, used in services.items():
                status = "✅ Active" if used else "❌ Simulation"
                print(f"     {service}: {status}")
    except Exception as e:
        print(f"❌ Alert Tool Error: {e}")

    # Test News Tool (Real Groq AI)
    print("\n📰 Testing Real News Tool (Groq AI)")
    print("-" * 40)

    news_config = MCPToolConfig(
        tool_name="test_news_tool",
        tool_type=MCPToolType.NEWS,
        priority_mapping={
            PriorityLevel.HIGH: ToolConfiguration(
                endpoint="mcp://news/high",
                timeout_seconds=60,
                max_retries=2,
                parameters={
                    "operations": ["current_disasters", "emergency_bulletin", "safety_instructions"]
                }
            )
        },
        fallback_tools=[],
        description="Test news tool for real Groq AI"
    )

    news_tool = NewsMCPTool(news_config)

    try:
        news_result = await news_tool.execute(alert_data, news_config.priority_mapping[PriorityLevel.HIGH])
        print(f"✅ News Tool Result: {news_result.status.value}")
        if news_result.response_data:
            print(
                f"   Operations attempted: {news_result.response_data.get('operations_attempted', 0)}")
            print(
                f"   Successful operations: {news_result.response_data.get('successful_operations', 0)}")
            print(
                f"   Groq service used: {'✅ Active' if news_result.response_data.get('groq_service_used', False) else '❌ Simulation'}")

            # Show sample results
            results = news_result.response_data.get('results', {})
            for operation, result in results.items():
                if result.get('success'):
                    print(f"   {operation}: ✅ Success")
                    if operation == 'current_disasters' and 'data' in result:
                        disasters = result['data'].get('disasters', [])
                        print(f"     Found {len(disasters)} current disasters")
                else:
                    print(f"   {operation}: ❌ Failed")
    except Exception as e:
        print(f"❌ News Tool Error: {e}")

    # Environment Check
    print("\n🔧 Environment Configuration Check")
    print("-" * 40)

    env_vars = {
        "GROQ_API_KEY": os.getenv('GROQ_API_KEY') or os.getenv('GROQ'),
        "TWILIO_ACCOUNT_SID": os.getenv('TWILIO_ACCOUNT_SID'),
        "TWILIO_AUTH_TOKEN": os.getenv('TWILIO_AUTH_TOKEN'),
        "TWILIO_PHONE_NUMBER": os.getenv('TWILIO_PHONE_NUMBER'),
        "SENDGRID_API_KEY": os.getenv('SENDGRID_API_KEY'),
        "SENDGRID_FROM_EMAIL": os.getenv('SENDGRID_FROM_EMAIL'),
        "FIREBASE_SERVICE_ACCOUNT_PATH": os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    }

    for var_name, var_value in env_vars.items():
        if var_value:
            # Show only first 10 and last 4 characters for security
            masked_value = var_value[:10] + "..." + \
                var_value[-4:] if len(var_value) > 14 else var_value[:6] + "..."
            print(f"   {var_name}: ✅ Set ({masked_value})")
        else:
            print(f"   {var_name}: ❌ Not set")

    print("\n" + "=" * 50)
    print("🏁 Real Notification Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_real_notifications())
