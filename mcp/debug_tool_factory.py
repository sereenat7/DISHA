#!/usr/bin/env python3
"""
Debug script to test MCP tool factory and concrete tool creation.
"""

import logging
import sys
import os
sys.path.append('.')
sys.path.append('./Backend')


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(message)s')


def test_tool_factory():
    """Test MCP tool factory and concrete tool creation."""

    try:
        print("🔍 Testing MCP Tool Factory...")

        # Import required modules
        from agentic_disaster_response.mcp_integration import MCPConfigurationManager
        from agentic_disaster_response.mcp_tools.tool_factory import MCPToolFactory, create_default_tool_registry

        print("✅ All imports successful")

        # Create default registry
        print("\n🏗️ Creating default tool registry...")
        registry = create_default_tool_registry()

        print(f"✅ Registry created with {len(registry.tools)} tools:")
        for tool_name, tool_config in registry.tools.items():
            print(
                f"  - {tool_name} ({tool_config.tool_type.value}): {'✅ Enabled' if tool_config.enabled else '❌ Disabled'}")

        # Test creating concrete tools
        print("\n🔧 Creating concrete tools...")
        try:
            concrete_tools = MCPToolFactory.create_tools_from_registry(
                registry, use_backup=False)
            print(f"✅ Created {len(concrete_tools)} concrete tools:")
            for tool_name, tool_instance in concrete_tools.items():
                print(f"  - {tool_name}: {type(tool_instance).__name__}")
        except Exception as e:
            print(f"❌ Failed to create concrete tools: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

        # Test creating backup tools
        print("\n🔧 Creating backup tools...")
        try:
            backup_tools = MCPToolFactory.create_tools_from_registry(
                registry, use_backup=True)
            print(f"✅ Created {len(backup_tools)} backup tools:")
            for tool_name, tool_instance in backup_tools.items():
                print(f"  - {tool_name}: {type(tool_instance).__name__}")
        except Exception as e:
            print(f"❌ Failed to create backup tools: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

        # Test AlertDispatcher initialization
        print("\n🚨 Testing AlertDispatcher initialization...")
        try:
            from agentic_disaster_response.alert_dispatcher import AlertDispatcher

            dispatcher = AlertDispatcher(registry)

            print(f"✅ AlertDispatcher created")
            print(f"  Concrete tools: {len(dispatcher.concrete_tools)}")
            print(f"  Backup tools: {len(dispatcher.backup_tools)}")

            if dispatcher.concrete_tools:
                print("  Concrete tools available:")
                for tool_name in dispatcher.concrete_tools.keys():
                    print(f"    - {tool_name}")
            else:
                print("  ❌ No concrete tools available!")

            if dispatcher.backup_tools:
                print("  Backup tools available:")
                for tool_name in dispatcher.backup_tools.keys():
                    print(f"    - {tool_name}")
            else:
                print("  ❌ No backup tools available!")

        except Exception as e:
            print(f"❌ Failed to create AlertDispatcher: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error during tool factory test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = test_tool_factory()
    if success:
        print("\n🎉 Tool Factory test completed successfully!")
    else:
        print("\n❌ Tool Factory test failed!")
