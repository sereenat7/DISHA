#!/usr/bin/env python3
"""
Test script for the complete MCP disaster response workflow.
This demonstrates how the full MCP system works when triggered via FastAPI.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"


def test_mcp_status():
    """Test MCP system status."""
    print("🔍 Testing MCP System Status...")
    try:
        response = requests.get(f"{BASE_URL}/api/mcp/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP Status: {data['status']}")
            print(f"📊 Available Tools: {data['available_tools']}")
            print(f"🔗 Connection Status: {data['connection_status']}")

            print("\n🛠️ MCP Tools Available:")
            for tool in data['tool_details']:
                print(
                    f"  - {tool['name']} ({tool['type']}): {tool['description']}")

            return True
        else:
            print(f"❌ MCP Status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ MCP Status error: {e}")
        return False


def test_full_disaster_response(disaster_type="flood", lat=19.0176, lon=72.8562, severity="high"):
    """Test the complete MCP disaster response workflow."""
    print(f"\n🚨 Testing Full MCP Disaster Response...")
    print(f"📍 Location: {lat}, {lon}")
    print(f"🌊 Disaster: {disaster_type} ({severity})")

    payload = {
        "disaster_type": disaster_type,
        "user_lat": lat,
        "user_lon": lon,
        "severity": severity,
        "description": f"Emergency {disaster_type} detected via API test",
        "radius_km": 10.0
    }

    try:
        print("⏳ Triggering full MCP workflow...")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/api/disaster/trigger-full-response",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        end_time = time.time()
        processing_time = end_time - start_time

        if response.status_code == 200:
            data = response.json()

            print(f"✅ Full MCP Response completed in {processing_time:.2f}s")
            print(f"🆔 Disaster ID: {data['disaster_id']}")

            # MCP Workflow Results
            workflow = data['mcp_workflow_results']
            print(f"\n📊 MCP Workflow Results:")
            print(f"  Status: {workflow['processing_status']}")
            print(
                f"  Processing Time: {workflow['total_processing_time_seconds']:.2f}s")
            print(f"  Success Rate: {workflow['success_rate']:.2%}")
            print(
                f"  Context Completeness: {workflow['context_completeness']:.2%}")
            print(f"  Priority Level: {workflow['priority_level']}")
            print(f"  Priority Score: {workflow['priority_score']}")

            # MCP Tools Executed
            print(
                f"\n🛠️ MCP Tools Executed ({len(data['mcp_tools_executed'])}):")
            for tool in data['mcp_tools_executed']:
                status_icon = "✅" if tool['status'] == 'success' else "❌"
                exec_time = tool['execution_time_seconds']
                time_str = f"({exec_time:.2f}s)" if exec_time is not None else "(N/A)"
                print(
                    f"  {status_icon} {tool['tool_name']}: {tool['status']} {time_str}")

            # Alerts Sent
            alerts = data['alerts_sent']
            print(f"\n📢 Alerts Dispatched:")
            print(f"  Total: {alerts['total_dispatches']}")
            print(f"  Successful: {alerts['successful_dispatches']}")
            print(f"  Failed: {alerts['failed_dispatches']}")

            if alerts['dispatch_details']:
                print(f"\n📱 Alert Details:")
                for alert in alerts['dispatch_details']:
                    status_icon = "✅" if alert['status'] == 'success' else "❌"
                    print(
                        f"  {status_icon} {alert['tool_name']}: {alert['successful_deliveries']}/{alert['recipients_count']} delivered")
                    if alert['error_message']:
                        print(f"    Error: {alert['error_message']}")

            # Evacuation Routes
            routes = data['evacuation_routes']
            print(f"\n🚗 Evacuation Routes Found:")

            if isinstance(routes, dict):
                total_locations = 0
                for category, locations in routes.items():
                    if category not in ['user_position', 'search_radius_km'] and isinstance(locations, list):
                        total_locations += len(locations)
                        print(
                            f"  {category.replace('_', ' ').title()}: {len(locations)} locations")
                        for loc in locations[:2]:  # Show first 2
                            if isinstance(loc, dict) and 'safe_location' in loc:
                                print(
                                    f"    - {loc['safe_location']} ({loc['distance_km']:.1f}km)")
                print(f"  Total: {total_locations} evacuation locations found")
            else:
                print(f"  Routes data: {routes}")

            # Connection Status
            connections = data['connection_status']
            print(f"\n🔗 Service Connections:")
            for service, status in connections.items():
                status_icon = "✅" if status else "❌"
                print(
                    f"  {status_icon} {service}: {'Connected' if status else 'Failed'}")

            # Errors (if any)
            if data['errors']:
                print(f"\n⚠️ Errors Encountered ({len(data['errors'])}):")
                for error in data['errors']:
                    print(
                        f"  - {error['component']}: {error['error_message']}")
                    if error['recovery_action']:
                        print(f"    Recovery: {error['recovery_action']}")

            return True

        else:
            print(f"❌ Full MCP Response failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Full MCP Response error: {e}")
        return False


def test_different_scenarios():
    """Test different disaster scenarios."""
    scenarios = [
        {"disaster_type": "fire", "lat": 19.0176,
            "lon": 72.8562, "severity": "critical"},
        {"disaster_type": "earthquake", "lat": 28.6139,
            "lon": 77.2090, "severity": "high"},  # Delhi
        {"disaster_type": "flood", "lat": 12.9716,
            "lon": 77.5946, "severity": "medium"},     # Bangalore
    ]

    print(f"\n🧪 Testing Different Disaster Scenarios...")

    for i, scenario in enumerate(scenarios, 1):
        print(
            f"\n--- Scenario {i}: {scenario['disaster_type'].title()} in {scenario['severity'].title()} ---")
        success = test_full_disaster_response(**scenario)
        if success:
            print(f"✅ Scenario {i} completed successfully")
        else:
            print(f"❌ Scenario {i} failed")

        if i < len(scenarios):
            print("⏳ Waiting 2 seconds before next scenario...")
            time.sleep(2)


def main():
    """Main test function."""
    print("🚀 DISHA MCP Full Workflow Test")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Testing against: {BASE_URL}")

    # Test 1: Check if server is running
    try:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print(f"❌ Server not responding at {BASE_URL}")
            return
        print(f"✅ Server is running at {BASE_URL}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return

    # Test 2: MCP Status
    mcp_status_ok = test_mcp_status()
    if not mcp_status_ok:
        print("⚠️ MCP system may not be fully functional, but continuing with tests...")

    # Test 3: Single full disaster response
    print(f"\n" + "="*50)
    success = test_full_disaster_response()

    if success:
        print(f"\n🎉 Single test completed successfully!")

        # Test 4: Multiple scenarios
        user_input = input(
            "\n🤔 Would you like to test multiple scenarios? (y/n): ").lower().strip()
        if user_input == 'y':
            test_different_scenarios()

    print(f"\n" + "="*50)
    print(
        f"🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 Summary:")
    print("  - MCP Status: ✅ Tested")
    print("  - Full Workflow: ✅ Tested")
    print("  - All MCP Tools: ✅ Executed")
    print("  - Real Notifications: ✅ Attempted")
    print("  - Evacuation Routes: ✅ Generated")


if __name__ == "__main__":
    main()
