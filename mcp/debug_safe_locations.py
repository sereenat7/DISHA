#!/usr/bin/env python3
"""
Debug script to test safe location finding and routing.
"""

from Backend.evacuation_system.main import get_safe_locations, get_route, find_evacuation_routes
import asyncio
import sys
import os
sys.path.append('.')


async def debug_safe_locations():
    """Debug the safe location finding process."""
    print("🔍 Debugging Safe Location Finding...")

    # Mumbai coordinates from your test
    lat, lon = 19.2307, 72.8567
    radius_km = 40.0

    print(f"📍 Location: {lat}, {lon}")
    print(f"🔄 Radius: {radius_km}km")

    # Step 1: Test get_safe_locations directly
    print("\n1️⃣ Testing get_safe_locations...")
    try:
        safe_locations = await get_safe_locations(lat, lon, radius_km)
        print(f"✅ Found {len(safe_locations)} safe locations")

        # Group by category
        by_category = {}
        for loc in safe_locations:
            category = loc["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(loc)

        for category, locations in by_category.items():
            print(f"   {category}: {len(locations)} locations")
            if locations:
                # Show first few
                for i, loc in enumerate(locations[:3]):
                    print(f"     - {loc['name']} ({loc['distance_km']:.2f}km)")
                if len(locations) > 3:
                    print(f"     ... and {len(locations) - 3} more")

    except Exception as e:
        print(f"❌ Error in get_safe_locations: {e}")
        return

    if not safe_locations:
        print("❌ No safe locations found - stopping here")
        return

    # Step 2: Test routing to first few locations
    print("\n2️⃣ Testing routing to first few locations...")
    test_locations = safe_locations[:5]  # Test first 5

    for i, loc in enumerate(test_locations):
        print(f"   Testing route {i+1}: {loc['name']} ({loc['category']})")
        try:
            route = await get_route(lat, lon, loc["lat"], loc["lon"])
            print(
                f"   ✅ Route found: {route['distance_m']/1000:.2f}km, {route['duration_s']/60:.1f}min")
        except Exception as e:
            print(f"   ❌ Route failed: {e}")

    # Step 3: Test full find_evacuation_routes
    print("\n3️⃣ Testing full find_evacuation_routes...")
    try:
        result = await find_evacuation_routes(lat, lon, radius_km, max_per_category=2)

        print(f"✅ Full result generated")
        print(f"   Alert ID: {result['alert_id']}")

        routes = result["results"]["routes"]
        for category, category_routes in routes.items():
            print(f"   {category}: {len(category_routes)} routes")
            for route in category_routes:
                print(
                    f"     - {route['safe_location']} ({route['distance_km']}km)")

        if all(len(routes[cat]) == 0 for cat in routes):
            print("❌ No routes in final result - all routing failed!")

    except Exception as e:
        print(f"❌ Error in find_evacuation_routes: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_safe_locations())
