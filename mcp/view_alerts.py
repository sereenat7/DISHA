#!/usr/bin/env python3
"""
Simple Alert Viewer for Agentic Disaster Response System
Quick script to check alerts and system outputs.
"""

import asyncio
import json
import httpx
from datetime import datetime


async def check_system_alerts():
    """Check and display current system alerts and status."""
    base_url = "http://127.0.0.1:8000"

    print("🚨 DISASTER RESPONSE SYSTEM - ALERT STATUS")
    print("=" * 60)
    print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        async with httpx.AsyncClient() as client:
            # 1. System Health Check
            print("🏥 SYSTEM HEALTH:")
            print("-" * 20)
            try:
                health_response = await client.get(f"{base_url}/system/health")
                if health_response.status_code == 200:
                    health = health_response.json()

                    # Overall status
                    evacuation_status = health.get(
                        "evacuation_system", "unknown")
                    agent_status = health.get(
                        "disaster_response_agent", "unknown")

                    print(f"🚨 Evacuation System: {evacuation_status.upper()}")
                    print(f"🤖 Disaster Agent: {agent_status.upper()}")

                    # Component details
                    if "agent_details" in health:
                        details = health["agent_details"]
                        active_disasters = details.get("active_disasters", 0)
                        print(f"📊 Active Disasters: {active_disasters}")

                        # Component status
                        components = details.get("component_status", {})
                        healthy_components = sum(
                            1 for status in components.values() if status)
                        total_components = len(components)
                        print(
                            f"🔧 Components: {healthy_components}/{total_components} healthy")

                        # Show unhealthy components
                        unhealthy = [name for name,
                                     status in components.items() if not status]
                        if unhealthy:
                            print(f"❌ Unhealthy: {', '.join(unhealthy)}")

                        # Recovery actions
                        recovery_actions = details.get("recovery_actions", [])
                        if recovery_actions:
                            print("🔄 Recovery Actions:")
                            for action in recovery_actions:
                                print(f"   • {action}")
                else:
                    print(
                        f"❌ Health check failed: HTTP {health_response.status_code}")
            except Exception as e:
                print(f"❌ Health check error: {e}")

            print()

            # 2. System Status with Metrics
            print("📊 SYSTEM METRICS:")
            print("-" * 20)
            try:
                status_response = await client.get(f"{base_url}/system/status")
                if status_response.status_code == 200:
                    status = status_response.json()

                    # System health summary
                    if "system_health" in status:
                        sys_health = status["system_health"]
                        overall_health = sys_health.get(
                            "overall_health", "unknown")
                        print(f"🔋 Overall Health: {overall_health.upper()}")

                    # Resource utilization
                    if "resource_utilization" in status:
                        resources = status["resource_utilization"]
                        slots_used = resources.get("concurrent_slots_used", 0)
                        max_slots = resources.get(
                            "max_concurrent_disasters", 0)
                        utilization = (slots_used / max_slots *
                                       100) if max_slots > 0 else 0
                        print(
                            f"💾 Resource Usage: {slots_used}/{max_slots} slots ({utilization:.1f}%)")

                    # Active processing
                    if "active_processing" in status:
                        processing = status["active_processing"]
                        disaster_count = processing.get("disaster_count", 0)
                        disasters = processing.get("disasters", [])
                        print(f"🔄 Processing: {disaster_count} disasters")
                        if disasters:
                            print("   Active Disaster IDs:")
                            for disaster_id in disasters:
                                print(f"   • {disaster_id}")

                    # Recent activity
                    if "recent_activity" in status:
                        activities = status["recent_activity"]
                        if activities:
                            print(
                                f"📝 Recent Activity: {len(activities)} events")
                            # Show last 3 activities
                            for activity in activities[-3:]:
                                print(f"   • {activity}")
                        else:
                            print("📝 Recent Activity: None")

                    # Evacuation system status
                    if "evacuation_system" in status:
                        evac_sys = status["evacuation_system"]
                        evac_status = evac_sys.get("status", "unknown")
                        endpoints = evac_sys.get("endpoints_available", [])
                        print(f"🚨 Evacuation System: {evac_status}")
                        print(f"🔗 Available Endpoints: {len(endpoints)}")

                else:
                    print(
                        f"❌ Status check failed: HTTP {status_response.status_code}")
            except Exception as e:
                print(f"❌ Status check error: {e}")

            print()

            # 3. Quick connectivity test
            print("🔗 CONNECTIVITY TEST:")
            print("-" * 20)
            try:
                # Test basic endpoint
                root_response = await client.get(f"{base_url}/")
                if root_response.status_code == 200:
                    print("✅ API Server: Connected")
                else:
                    print(f"❌ API Server: HTTP {root_response.status_code}")

                # Test docs endpoint
                docs_response = await client.get(f"{base_url}/docs")
                if docs_response.status_code == 200:
                    print("✅ API Documentation: Available")
                else:
                    print(
                        f"❌ API Documentation: HTTP {docs_response.status_code}")

            except Exception as e:
                print(f"❌ Connectivity error: {e}")

            print()
            print("=" * 60)
            print("💡 TIP: Use 'python monitor_alerts.py' for detailed monitoring")
            print(
                "💡 TIP: Check server logs with 'uvicorn app:app --reload' for real-time alerts")

    except Exception as e:
        print(f"❌ System check failed: {e}")
        print()
        print("🔧 TROUBLESHOOTING:")
        print("1. Make sure the server is running: uvicorn app:app --reload")
        print("2. Check if the server is accessible at http://127.0.0.1:8000")
        print("3. Verify no firewall is blocking port 8000")


if __name__ == "__main__":
    asyncio.run(check_system_alerts())
