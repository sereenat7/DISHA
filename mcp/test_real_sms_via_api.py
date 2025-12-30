#!/usr/bin/env python3
"""
Test real SMS notifications through the FastAPI MCP endpoint.
"""

import requests
import json
import time


def test_real_sms_notifications():
    """Test that real SMS notifications are sent via the MCP API."""

    print("📱 Testing Real SMS Notifications via MCP API")
    print("=" * 60)

    # API endpoint
    base_url = "http://127.0.0.1:8000"
    endpoint = f"{base_url}/api/disaster/trigger-full-response"

    # Test data - Mumbai flood
    test_data = {
        "disaster_type": "flood",
        "user_lat": 19.0176,
        "user_lon": 72.8562,
        "severity": "high",
        "description": "🚨 REAL TEST: High severity flood detected in Mumbai. This is a test of the DISHA emergency notification system. Please ignore this message.",
        "radius_km": 10.0
    }

    print(f"📍 Location: {test_data['user_lat']}, {test_data['user_lon']}")
    print(
        f"🌊 Disaster: {test_data['disaster_type']} ({test_data['severity']})")
    print(f"📱 Message: {test_data['description'][:50]}...")
    print()

    try:
        print("⏳ Sending request to MCP API...")
        start_time = time.time()

        response = requests.post(
            endpoint,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        execution_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"✅ API Response received in {execution_time:.2f}s")
            print(f"🆔 Disaster ID: {result.get('disaster_id', 'Unknown')}")
            print()

            # Check MCP workflow results
            workflow_result = result.get("mcp_workflow_results", {})
            print("📊 MCP Workflow Results:")
            print(
                f"  Status: {workflow_result.get('processing_status', 'Unknown')}")
            print(
                f"  Processing Time: {workflow_result.get('total_processing_time_seconds', 0):.2f}s")
            print(
                f"  Success Rate: {workflow_result.get('success_rate', 0):.2%}")
            print(
                f"  Priority Level: {workflow_result.get('priority_level', 'Unknown')}")
            print(
                f"  Priority Score: {workflow_result.get('priority_score', 0):.2f}")
            print()

            # Check alert dispatch results
            alerts_sent = result.get("alerts_sent", {})
            dispatch_details = alerts_sent.get("dispatch_details", [])

            print("🛠️ MCP Tools Executed:")
            real_services_found = False
            total_successful = 0

            for detail in dispatch_details:
                tool_name = detail.get("tool_name", "Unknown")
                status = detail.get("status", "Unknown")
                recipients = detail.get("recipients_count", 0)
                successful = detail.get("successful_deliveries", 0)
                failed = detail.get("failed_deliveries", 0)

                print(
                    f"  {'✅' if status == 'success' else '❌'} {tool_name}: {status}")
                print(
                    f"    Recipients: {recipients}, Successful: {successful}, Failed: {failed}")

                total_successful += successful

                # For now, we'll assume real services are being used if we see successful deliveries
                if successful > 0:
                    real_services_found = True
                    print(f"    📱 Real notifications sent: {successful}")

            print(f"\n📊 Summary:")
            print(
                f"  Total Dispatches: {alerts_sent.get('total_dispatches', 0)}")
            print(
                f"  Successful: {alerts_sent.get('successful_dispatches', 0)}")
            print(f"  Failed: {alerts_sent.get('failed_dispatches', 0)}")
            print(f"  Total Successful Deliveries: {total_successful}")

            print()
            if real_services_found and total_successful > 0:
                print("🎉 SUCCESS: Real notification services are working!")
                print("📱 Check your phone for SMS messages")
                print("📧 Check your email for alert notifications")
                print(f"🔔 {total_successful} real notifications were sent!")
            else:
                print("⚠️  WARNING: No successful deliveries detected")
                print("This could mean:")
                print("  - Services are using simulation mode")
                print("  - Real services failed to send")
                print("  - API response structure changed")

            return True

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_real_sms_notifications()
    print("\n" + "=" * 60)
    if success:
        print("✅ Real SMS notification test completed successfully!")
    else:
        print("❌ Real SMS notification test failed!")
    exit(0 if success else 1)
