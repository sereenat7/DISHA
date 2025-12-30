#!/usr/bin/env python3
"""
Alert and System Monitor for Agentic Disaster Response System
This script helps you monitor alerts, system status, and disaster processing results.
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List
import time


class DisasterSystemMonitor:
    """Monitor the disaster response system for alerts and status."""

    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.disaster_ids = []

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/system/health")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status with metrics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/system/status")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def trigger_test_disaster(self, disaster_type: str = "fire") -> str:
        """Trigger a test disaster and return the disaster ID."""
        try:
            disaster_request = {
                "disaster_type": disaster_type,
                "location_lat": 52.5200,
                "location_lon": 13.4050,
                "severity": "high",
                "affected_radius_km": 5.0,
                "description": f"Test {disaster_type} disaster for monitoring",
                "estimated_affected_population": 1500
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/disaster/trigger",
                    json=disaster_request
                )

                if response.status_code == 200:
                    result = response.json()
                    disaster_id = result.get("disaster_id")
                    self.disaster_ids.append(disaster_id)
                    return disaster_id
                else:
                    return f"Error: HTTP {response.status_code}"

        except Exception as e:
            return f"Error: {str(e)}"

    async def get_disaster_status(self, disaster_id: str) -> Dict[str, Any]:
        """Get status of a specific disaster."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/disaster/{disaster_id}/status")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def print_health_status(self, health_data: Dict[str, Any]):
        """Print formatted health status."""
        print("\n🏥 SYSTEM HEALTH STATUS")
        print("=" * 50)

        if "error" in health_data:
            print(f"❌ Error: {health_data['error']}")
            return

        print(f"⏰ Timestamp: {health_data.get('timestamp', 'Unknown')}")
        print(
            f"🔋 Evacuation System: {health_data.get('evacuation_system', 'Unknown')}")
        print(
            f"🤖 Disaster Response Agent: {health_data.get('disaster_response_agent', 'Unknown')}")

        if "agent_details" in health_data:
            details = health_data["agent_details"]
            print(f"📊 Active Disasters: {details.get('active_disasters', 0)}")

            print("\n🔧 Component Status:")
            components = details.get("component_status", {})
            for component, status in components.items():
                status_icon = "✅" if status else "❌"
                print(
                    f"   {status_icon} {component}: {'healthy' if status else 'unhealthy'}")

            recovery_actions = details.get("recovery_actions", [])
            if recovery_actions:
                print("\n🔄 Recovery Actions:")
                for action in recovery_actions:
                    print(f"   • {action}")

    def print_system_status(self, status_data: Dict[str, Any]):
        """Print formatted system status."""
        print("\n📊 DETAILED SYSTEM STATUS")
        print("=" * 50)

        if "error" in status_data:
            print(f"❌ Error: {status_data['error']}")
            return

        print(f"⏰ Timestamp: {status_data.get('timestamp', 'Unknown')}")

        # System Health
        if "system_health" in status_data:
            health = status_data["system_health"]
            print(
                f"🔋 Overall Health: {health.get('overall_health', 'Unknown')}")

        # Active Processing
        if "active_processing" in status_data:
            processing = status_data["active_processing"]
            print(f"🔄 Active Disasters: {processing.get('disaster_count', 0)}")

            disasters = processing.get("disasters", [])
            if disasters:
                print("   Active Disaster IDs:")
                for disaster in disasters:
                    print(f"   • {disaster}")

        # Resource Utilization
        if "resource_utilization" in status_data:
            resources = status_data["resource_utilization"]
            print(
                f"💾 Concurrent Slots Used: {resources.get('concurrent_slots_used', 0)}/{resources.get('max_concurrent_disasters', 0)}")

        # Recent Activity
        if "recent_activity" in status_data:
            activities = status_data["recent_activity"]
            if activities:
                print("\n📝 Recent Activity:")
                for activity in activities[-5:]:  # Show last 5 activities
                    print(f"   • {activity}")
            else:
                print("\n📝 Recent Activity: None")

    def print_disaster_status(self, disaster_id: str, status_data: Dict[str, Any]):
        """Print formatted disaster status."""
        print(f"\n🚨 DISASTER STATUS: {disaster_id}")
        print("=" * 50)

        if "error" in status_data:
            print(f"❌ Error: {status_data['error']}")
            return

        print(f"📋 Status: {status_data.get('processing_status', 'Unknown')}")
        print(f"💬 Message: {status_data.get('message', 'No message')}")

        if "processing_started_at" in status_data:
            print(f"⏰ Started: {status_data['processing_started_at']}")

        if "estimated_completion_time" in status_data:
            print(
                f"🎯 Est. Completion: {status_data['estimated_completion_time']}")

    async def monitor_disaster_processing(self, disaster_id: str, max_wait_seconds: int = 60):
        """Monitor a disaster processing until completion or timeout."""
        print(f"\n👀 MONITORING DISASTER: {disaster_id}")
        print("=" * 50)

        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            status = await self.get_disaster_status(disaster_id)

            if "error" not in status:
                processing_status = status.get("processing_status", "unknown")
                print(
                    f"⏰ {datetime.now().strftime('%H:%M:%S')} - Status: {processing_status}")

                if processing_status in ["completed", "failed", "completed_or_not_started"]:
                    print(
                        f"✅ Monitoring complete. Final status: {processing_status}")
                    self.print_disaster_status(disaster_id, status)
                    break
            else:
                print(f"❌ Error checking status: {status['error']}")

            await asyncio.sleep(2)  # Check every 2 seconds
        else:
            print(f"⏰ Monitoring timeout after {max_wait_seconds} seconds")

    async def run_comprehensive_monitor(self):
        """Run a comprehensive monitoring session."""
        print("🚀 AGENTIC DISASTER RESPONSE SYSTEM MONITOR")
        print("=" * 60)

        # 1. Check system health
        health = await self.get_system_health()
        self.print_health_status(health)

        # 2. Check detailed system status
        status = await self.get_system_status()
        self.print_system_status(status)

        # 3. Trigger a test disaster
        print(f"\n🔥 TRIGGERING TEST DISASTER")
        print("=" * 50)
        disaster_id = await self.trigger_test_disaster("fire")

        if disaster_id.startswith("disaster_"):
            print(f"✅ Test disaster triggered: {disaster_id}")

            # 4. Monitor the disaster processing
            await self.monitor_disaster_processing(disaster_id, max_wait_seconds=30)

            # 5. Final system status check
            print(f"\n📊 FINAL SYSTEM STATUS")
            print("=" * 50)
            final_status = await self.get_system_status()
            self.print_system_status(final_status)
        else:
            print(f"❌ Failed to trigger disaster: {disaster_id}")

    async def continuous_monitor(self, interval_seconds: int = 10):
        """Run continuous monitoring with regular status updates."""
        print("🔄 CONTINUOUS MONITORING MODE")
        print("=" * 50)
        print(f"Checking system status every {interval_seconds} seconds...")
        print("Press Ctrl+C to stop")

        try:
            while True:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 30)

                # Quick health check
                health = await self.get_system_health()
                if "error" not in health:
                    agent_status = health.get(
                        "disaster_response_agent", "unknown")
                    evacuation_status = health.get(
                        "evacuation_system", "unknown")
                    print(
                        f"🤖 Agent: {agent_status} | 🚨 Evacuation: {evacuation_status}")

                    if "agent_details" in health:
                        active_disasters = health["agent_details"].get(
                            "active_disasters", 0)
                        print(f"📊 Active Disasters: {active_disasters}")
                else:
                    print(f"❌ Health Check Error: {health['error']}")

                await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")


async def main():
    """Main function with menu options."""
    monitor = DisasterSystemMonitor()

    print("🚀 AGENTIC DISASTER RESPONSE SYSTEM MONITOR")
    print("=" * 60)
    print("Choose monitoring mode:")
    print("1. Comprehensive Monitor (health + test disaster)")
    print("2. Continuous Monitor (live status updates)")
    print("3. Health Check Only")
    print("4. Trigger Test Disaster")
    print("5. Exit")

    try:
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            await monitor.run_comprehensive_monitor()
        elif choice == "2":
            interval = input(
                "Enter monitoring interval in seconds (default 10): ").strip()
            interval = int(interval) if interval.isdigit() else 10
            await monitor.continuous_monitor(interval)
        elif choice == "3":
            health = await monitor.get_system_health()
            monitor.print_health_status(health)
            status = await monitor.get_system_status()
            monitor.print_system_status(status)
        elif choice == "4":
            disaster_type = input(
                "Enter disaster type (fire/flood/earthquake, default: fire): ").strip()
            disaster_type = disaster_type if disaster_type else "fire"
            disaster_id = await monitor.trigger_test_disaster(disaster_type)
            print(f"🚨 Triggered disaster: {disaster_id}")
            if disaster_id.startswith("disaster_"):
                await monitor.monitor_disaster_processing(disaster_id)
        elif choice == "5":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")

    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
