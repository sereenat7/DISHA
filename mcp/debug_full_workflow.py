#!/usr/bin/env python3
"""
Debug script to test the full MCP workflow and see where it's failing.
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


async def test_full_mcp_workflow():
    """Test the full MCP workflow to identify where it's failing."""

    try:
        print("🔍 Testing Full MCP Workflow...")

        # Import required modules
        from agentic_disaster_response.mcp_integration import MCPConfigurationManager
        from agentic_disaster_response.disaster_response_agent import DisasterResponseAgent, AgentConfiguration
        from agentic_disaster_response.models.disaster_data import DisasterData, DisasterType, SeverityLevel
        from agentic_disaster_response.models.location import Location

        print("✅ All imports successful")

        # Initialize MCP system
        print("\n🏗️ Initializing MCP system...")
        config_manager = MCPConfigurationManager()
        config_manager.load_default_configurations()
        mcp_registry = config_manager.get_registry()

        agent_config = AgentConfiguration(
            context_search_radius_km=10.0,
            max_routes_per_category=3,
            enable_concurrent_processing=True,
            enable_performance_monitoring=True
        )

        agent = DisasterResponseAgent(mcp_registry, agent_config)
        print("✅ DisasterResponseAgent created")

        # Check AlertDispatcher tool status
        dispatcher = agent.alert_dispatcher
        print(f"\n📊 AlertDispatcher Status:")
        print(f"  Concrete tools: {len(dispatcher.concrete_tools)}")
        print(f"  Backup tools: {len(dispatcher.backup_tools)}")

        if dispatcher.concrete_tools:
            print("  Available concrete tools:")
            for tool_name in dispatcher.concrete_tools.keys():
                print(f"    - {tool_name}")

        # Initialize connections
        print("\n🔗 Initializing connections...")
        connection_status = await agent.initialize_connections()
        print(f"Connection status: {connection_status}")

        # Create test disaster data and store it in the system
        print("\n🌊 Creating test disaster data...")
        disaster_id = f"debug_workflow_{int(datetime.now().timestamp())}"

        location = Location(
            latitude=19.0176,
            longitude=72.8562,
            address="Mumbai, Maharashtra, India",
            administrative_area="Mumbai"
        )

        disaster_data = DisasterData(
            disaster_id=disaster_id,
            disaster_type=DisasterType.FLOOD,
            location=location,
            severity=SeverityLevel.HIGH,
            timestamp=datetime.now(),
            affected_areas=[location],
            estimated_impact=None,
            description="Debug test flood for full workflow",
            source="debug_script"
        )

        # Store disaster data in the system (simulate FastAPI backend storage)
        if not hasattr(agent, '_disaster_storage'):
            # Create storage if it doesn't exist
            agent._disaster_storage = {}
        agent._disaster_storage[disaster_id] = disaster_data

        print(f"✅ Test disaster data created with ID: {disaster_id}")

        # Execute full disaster response
        print("\n🚀 Executing full disaster response...")
        response = await agent.process_disaster_event(disaster_id)

        print(f"\n📊 Disaster Response Results:")
        print(f"  Status: {response.processing_status}")
        print(
            f"  Processing Time: {response.total_processing_time_seconds:.2f}s")
        print(f"  Success Rate: {response.success_rate:.2%}")
        print(f"  Context Completeness: {response.context_completeness:.2%}")
        print(f"  Priority Level: {response.priority_level}")
        print(f"  Priority Score: {response.priority_score}")

        # Check MCP tool results
        print(f"\n🛠️ MCP Tool Results ({len(response.mcp_tool_results)}):")
        for tool_result in response.mcp_tool_results:
            status_icon = "✅" if tool_result.status == 'success' else "❌"
            exec_time = tool_result.execution_time_seconds or 0
            print(
                f"  {status_icon} {tool_result.tool_name}: {tool_result.status} ({exec_time:.2f}s)")
            if tool_result.error_message:
                print(f"    Error: {tool_result.error_message}")

        # Check alert dispatch results
        print(f"\n📢 Alert Dispatch Results:")
        if hasattr(response, 'alert_dispatch_result') and response.alert_dispatch_result:
            dispatch = response.alert_dispatch_result
            print(f"  Total dispatches: {dispatch.total_tools_attempted}")
            print(f"  Successful: {dispatch.successful_dispatches}")
            print(f"  Failed: {dispatch.failed_dispatches}")
            print(f"  Fallback used: {dispatch.fallback_used}")

            if dispatch.execution_results:
                print("  Execution details:")
                for result in dispatch.execution_results:
                    status_icon = "✅" if result.status.value == 'success' else "❌"
                    print(
                        f"    {status_icon} {result.tool_name}: {result.status.value}")
                    if result.error_message:
                        print(f"      Error: {result.error_message}")
        else:
            print("  No alert dispatch results available")

        return response.success_rate > 0

    except Exception as e:
        print(f"❌ Error during full workflow test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_mcp_workflow())
    if success:
        print("\n🎉 Full MCP Workflow test completed with some success!")
    else:
        print("\n❌ Full MCP Workflow test failed completely!")
