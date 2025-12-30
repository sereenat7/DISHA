#!/usr/bin/env python3
"""
Startup script for the Agentic Disaster Response System.
This script helps you run the complete system with proper setup.
"""

import asyncio
import subprocess
import time
import sys
import os
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")

    required_packages = [
        'fastapi', 'uvicorn', 'httpx', 'pydantic', 'hypothesis'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("   Install with: pip install " + " ".join(missing_packages))
        return False

    print("✅ All dependencies are installed")
    return True


def start_fastapi_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting FastAPI server...")

    backend_path = Path("Backend/evacuation_system")
    if not backend_path.exists():
        print("❌ Backend directory not found")
        return None

    try:
        # Start uvicorn server
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"
        ], cwd=backend_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait a moment for server to start
        time.sleep(3)

        if process.poll() is None:
            print("✅ FastAPI server started on http://127.0.0.1:8000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ FastAPI server failed to start")
            print(f"   Error: {stderr.decode()}")
            return None

    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return None


async def test_disaster_response():
    """Test the disaster response system."""
    print("\n🧪 Testing Disaster Response System...")

    try:
        # Import and run the system test
        from test_system import SystemTester

        tester = SystemTester()
        await tester.run_complete_test()

    except ImportError as e:
        print(f"❌ Failed to import test system: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")


def show_usage_instructions():
    """Show usage instructions."""
    print("\n" + "=" * 60)
    print("📋 USAGE INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1. 🌐 FastAPI Backend:")
    print("   - Access API docs: http://127.0.0.1:8000/docs")
    print("   - Health check: http://127.0.0.1:8000/health")
    print("   - Evacuation routes: http://127.0.0.1:8000/evacuation-routes")
    print()
    print("2. 🤖 Disaster Response Agent:")
    print("   - The agent runs automatically when disasters are triggered")
    print("   - It processes disasters through the complete workflow")
    print("   - Integrates with MCP tools for alert dispatch")
    print()
    print("3. 🔧 MCP Tools:")
    print("   - Alert Tool: Handles emergency notifications")
    print("   - Routing Tool: Manages evacuation route information")
    print("   - Context Tool: Provides situational awareness")
    print("   - Backup Tools: Fallback mechanisms for reliability")
    print()
    print("4. 📊 Testing:")
    print("   - Run: python test_system.py")
    print("   - Or use the integrated test in this script")
    print()
    print("5. 🛑 To Stop:")
    print("   - Press Ctrl+C to stop this script")
    print("   - The FastAPI server will be terminated automatically")
    print()


async def main():
    """Main function to run the complete system."""
    print("🚀 Agentic Disaster Response System")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return

    # Start FastAPI server
    fastapi_process = start_fastapi_server()
    if not fastapi_process:
        print("❌ Cannot continue without FastAPI server")
        return

    try:
        # Show usage instructions
        show_usage_instructions()

        # Test the system
        await test_disaster_response()

        print("\n🎯 System is running successfully!")
        print("   FastAPI server: http://127.0.0.1:8000")
        print("   Press Ctrl+C to stop")

        # Keep the script running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️  Shutting down system...")
    except Exception as e:
        print(f"\n❌ System error: {e}")
    finally:
        # Clean up
        if fastapi_process and fastapi_process.poll() is None:
            print("🛑 Stopping FastAPI server...")
            fastapi_process.terminate()
            fastapi_process.wait()
            print("✅ FastAPI server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
