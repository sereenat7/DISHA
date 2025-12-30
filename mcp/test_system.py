#!/usr/bin/env python3
"""
Test script to demonstrate the Agentic Disaster Response system.
This script shows how to run and test the complete MCP server system.
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any

# Import the disaster response system
from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
from agentic_disaster_response.mcp_tools.tool_factory import create_default_tool_registry
from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
from agentic_disaster_response.models.location import Location


class SystemTester:
    """Test the complete disaster response system."""

    def __init__(self):
        self.fastapi_url = "http://127.0.0.1:8000"
        self.agent = None

    async def initialize_agent(self):
        """Initialize the disaster response agent."""
        print("🚀 Initializing Disaster Response Agent...")

        # Create MCP tool registry
        registry = create_default_tool_registry()

        # Create agent configuration
        config = AgentConfiguration(
            context_search_radius_km=10.0,
            max_routes_per_category=3,
            enable_concurrent_processing=True,
            max_concurrent_disasters=5,
            enable_performance_monitoring=True
        )

        # Initialize agent
        self.agent = DisasterResponseAgent(registry, config)
        await self.agent.initialize_connections()

        print("✅ Agent initialized successfully!")
        return self.agent

    async def test_fastapi_backend(self):
        """Test the FastAPI backend connectivity."""
        print("\n🔗 Testing FastAPI Backend...")

        try:
            async with httpx.AsyncClient() as client:
                # Test health endpoint
                response = await client.get(f"{self.fastapi_url}/health")
                if response.status_code == 200:
                    print("✅ FastAPI backend is healthy")
                    print(f"   Response: {response.json()}")
                else:
                    print(
                        f"❌ FastAPI backend health check failed: {response.status_code}")

                # Test evacuation routes endpoint
                response = await client.get(f"{self.fastapi_url}/docs")
                if response.status_code == 200:
                    print("✅ FastAPI documentation is accessible")
                else:
                    print(
                        f"❌ FastAPI docs not accessible: {response.status_code}")

        except Exception as e:
            print(f"❌ FastAPI backend connection failed: {e}")

    async def test_disaster_processing(self):
        """Test end-to-end disaster processing."""
        print("\n🚨 Testing Disaster Processing...")

        if not self.agent:
            print("❌ Agent not initialized")
            return

        # Create test disaster data first
        disaster_id = f"test_disaster_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Test with FastAPI backend first
        try:
            print(f"   Creating disaster via FastAPI: {disaster_id}")

            async with httpx.AsyncClient() as client:
                disaster_request = {
                    "disaster_type": "fire",
                    "location_lat": 52.5200,
                    "location_lon": 13.4050,
                    "severity": "high",
                    "affected_radius_km": 5.0,
                    "description": "Test fire disaster for system validation",
                    "estimated_affected_population": 2000
                }

                response = await client.post(
                    f"{self.fastapi_url}/disaster/trigger",
                    json=disaster_request
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Disaster triggered via FastAPI!")
                    print(
                        f"   Disaster ID: {result.get('disaster_id', 'unknown')}")
                    print(f"   Status: {result.get('status', 'unknown')}")
                    return
                else:
                    print(
                        f"⚠️  FastAPI trigger failed ({response.status_code}), testing agent directly")

        except Exception as e:
            print(f"⚠️  FastAPI test failed: {e}, testing agent directly")

        # Test disaster processing
        try:
            print(f"   Processing disaster directly: {disaster_id}")
            response = await self.agent.process_disaster_event(disaster_id)

            if response:
                print(f"✅ Disaster processed successfully!")
                print(f"   Status: {response.processing_status}")
                print(
                    f"   Processing time: {response.total_processing_time_seconds:.2f}s")

                if response.context:
                    print(
                        f"   Context completeness: {response.context.context_completeness:.2f}")

                if response.priority:
                    print(
                        f"   Priority: {response.priority.level.value} (score: {response.priority.score:.2f})")

                if response.dispatch_results:
                    print(
                        f"   Alerts dispatched: {len(response.dispatch_results)}")
            else:
                print("❌ No response received from disaster processing")

        except Exception as e:
            print(f"❌ Disaster processing failed: {e}")

    async def test_mcp_tools(self):
        """Test MCP tools functionality."""
        print("\n🔧 Testing MCP Tools...")

        if not self.agent:
            print("❌ Agent not initialized")
            return

        try:
            # Test alert dispatcher
            dispatcher = self.agent.alert_dispatcher
            if dispatcher:
                print("✅ Alert dispatcher is available")

                # Check available tools
                if hasattr(dispatcher, 'primary_tools'):
                    print(f"   Primary tools: {len(dispatcher.primary_tools)}")
                if hasattr(dispatcher, 'backup_tools'):
                    print(f"   Backup tools: {len(dispatcher.backup_tools)}")
            else:
                print("❌ Alert dispatcher not available")

        except Exception as e:
            print(f"❌ MCP tools test failed: {e}")

    async def test_system_health(self):
        """Test system health monitoring."""
        print("\n💊 Testing System Health...")

        if not self.agent:
            print("❌ Agent not initialized")
            return

        try:
            health_status = await self.agent.monitor_system_health()

            print("✅ System health check completed")
            print(
                f"   Overall health: {health_status.get('overall_health', 'unknown')}")

            components = health_status.get('component_status', {})
            for component, status in components.items():
                status_icon = "✅" if status else "❌"
                print(
                    f"   {status_icon} {component}: {'healthy' if status else 'unhealthy'}")

        except Exception as e:
            print(f"❌ System health check failed: {e}")

    async def run_complete_test(self):
        """Run the complete system test."""
        print("🎯 Starting Complete System Test")
        print("=" * 50)

        # Test FastAPI backend
        await self.test_fastapi_backend()

        # Initialize agent
        await self.initialize_agent()

        # Test MCP tools
        await self.test_mcp_tools()

        # Test system health
        await self.test_system_health()

        # Test disaster processing
        await self.test_disaster_processing()

        print("\n" + "=" * 50)
        print("🏁 System Test Complete!")


async def main():
    """Main test function."""
    tester = SystemTester()
    await tester.run_complete_test()


if __name__ == "__main__":
    print("🚀 Agentic Disaster Response System Tester")
    print("This script tests the complete MCP server system")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
