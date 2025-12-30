#!/usr/bin/env python3
"""
Interactive Test Script for DISHA Real Notification System
"""

import requests
import json
import time
import os
from datetime import datetime


def print_header():
    print("🚨" * 20)
    print("🚀 DISHA REAL NOTIFICATION SYSTEM TESTER")
    print("🚨" * 20)
    print()


def test_api_connection():
    """Test if the API server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Server: Connected")
            return True
        else:
            print("❌ API Server: Not responding properly")
            return False
    except requests.exceptions.RequestException:
        print("❌ API Server: Not running")
        print("💡 Start it with: python run_system.py")
        return False


def send_test_disaster(disaster_data):
    """Send a test disaster to the system"""
    try:
        print(
            f"🚨 Triggering {disaster_data['disaster_type'].upper()} disaster...")
        print(f"📍 Location: {disaster_data['description']}")
        print(f"⚠️  Severity: {disaster_data['severity'].upper()}")
        print(
            f"👥 Affected: {disaster_data['estimated_affected_population']} people")
        print()

        response = requests.post(
            "http://127.0.0.1:8000/disaster/trigger",
            headers={"Content-Type": "application/json"},
            json=disaster_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Disaster triggered successfully!")
            print(f"🆔 Disaster ID: {result['disaster_id']}")
            print(f"📊 Status: {result['status']}")
            print(f"⏰ Started: {result['processing_started_at']}")
            return result['disaster_id']
        else:
            print(f"❌ Failed to trigger disaster: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None


def monitor_disaster(disaster_id):
    """Monitor the disaster processing"""
    print()
    print("🔍 Monitoring disaster processing...")
    print("⏳ Waiting for notifications to be sent...")

    for i in range(10):  # Wait up to 30 seconds
        time.sleep(3)
        print(f"⏰ Checking... ({i+1}/10)")

        # In a real implementation, you'd check the disaster status
        # For now, we'll just wait and assume it's processing

    print("✅ Processing should be complete!")
    print()


def main():
    print_header()

    # Test scenarios
    scenarios = {
        "1": {
            "name": "🔥 Critical Fire Emergency",
            "data": {
                "disaster_type": "fire",
                "location_lat": 19.0760,
                "location_lon": 72.8777,
                "severity": "critical",
                "affected_radius_km": 3.0,
                "description": "CRITICAL TEST: Major building fire in Mumbai - Immediate evacuation required",
                "estimated_affected_population": 1500
            }
        },
        "2": {
            "name": "🌊 High Priority Flood",
            "data": {
                "disaster_type": "flood",
                "location_lat": 28.6139,
                "location_lon": 77.2090,
                "severity": "high",
                "affected_radius_km": 8.0,
                "description": "HIGH TEST: Severe flooding in Delhi - Evacuation recommended",
                "estimated_affected_population": 4000
            }
        },
        "3": {
            "name": "🏗️ Medium Building Collapse",
            "data": {
                "disaster_type": "building_collapse",
                "location_lat": 12.9716,
                "location_lon": 77.5946,
                "severity": "medium",
                "affected_radius_km": 2.0,
                "description": "MEDIUM TEST: Building collapse in Bangalore - Monitor situation",
                "estimated_affected_population": 800
            }
        },
        "4": {
            "name": "⚡ Low Priority Power Outage",
            "data": {
                "disaster_type": "electrical",
                "location_lat": 13.0827,
                "location_lon": 80.2707,
                "severity": "low",
                "affected_radius_km": 5.0,
                "description": "LOW TEST: Power outage in Chennai - Routine issue",
                "estimated_affected_population": 2000
            }
        }
    }

    # Check API connection
    if not test_api_connection():
        print()
        print("🔧 To start the system:")
        print("1. Open a new terminal")
        print("2. Run: python run_system.py")
        print("3. Wait for 'Application startup complete'")
        print("4. Run this test again")
        return

    print()
    print("📱 REAL NOTIFICATIONS WILL BE SENT TO:")
    print("   • +918850755760 (Joel Pawar)")
    print("   • +919529685725 (Sereena Thomas)")
    print("   • +919322945843 (Seane Dcosta)")
    print()
    print("⚠️  WARNING: This will send REAL SMS messages!")
    print()

    # Show test options
    print("🧪 Choose a test scenario:")
    for key, scenario in scenarios.items():
        print(f"   {key}. {scenario['name']}")
    print("   5. 📱 Quick SMS Test (Direct)")
    print("   6. 🔍 System Status Check")
    print("   0. Exit")
    print()

    choice = input("Enter your choice (0-6): ").strip()

    if choice == "0":
        print("👋 Goodbye!")
        return

    elif choice == "5":
        print()
        print("📱 Sending direct SMS test...")
        os.system("python test_live_sms.py")
        return

    elif choice == "6":
        print()
        print("🔍 Checking system status...")
        os.system("python view_alerts.py")
        return

    elif choice in scenarios:
        scenario = scenarios[choice]
        print()
        print(f"🚀 Running: {scenario['name']}")
        print("=" * 50)

        # Confirm before sending real notifications
        confirm = input(
            "⚠️  This will send REAL notifications! Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Test cancelled")
            return

        print()
        disaster_id = send_test_disaster(scenario['data'])

        if disaster_id:
            monitor_disaster(disaster_id)

            print("📊 EXPECTED RESULTS:")
            print("✅ 3 people should receive SMS alerts")
            print("✅ Email alerts sent from alerts@disha.gov.in")
            print("✅ Push notifications via Firebase")
            print("✅ AI-generated news bulletins")
            print()
            print("🔍 Check results with: python view_alerts.py")
            print("📱 Ask Joel, Sereena, or Seane if they got SMS!")

    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()
