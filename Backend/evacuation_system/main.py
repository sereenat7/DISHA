# evacuation_logic.py
import httpx
import uuid
import math
import asyncio

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth (in kilometers).
    """
    R = 6371  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


async def get_safe_locations(lat: float, lon: float, radius_km: float):
    """
    Fetch safe locations (hospitals, shelters/bunkers, underground parking) around a point using Overpass API.
    """
    radius_m = int(radius_km * 1000)

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="shelter"](around:{radius_m},{lat},{lon});
      node["building"="bunker"](around:{radius_m},{lat},{lon});
      node["amenity"="parking"]["parking"="underground"](around:{radius_m},{lat},{lon});
    );
    out body;
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OVERPASS_URL, data=query)

    if response.status_code != 200 or not response.text.strip():
        return []

    data = response.json()
    locations = []

    for element in data.get("elements", []):
        el_lat = element.get("lat")
        el_lon = element.get("lon")
        if el_lat is None or el_lon is None:
            continue

        tags = element.get("tags", {})
        name = tags.get("name", "Unnamed Safe Location")

        # Categorize
        if tags.get("amenity") == "hospital":
            category = "hospitals"
        elif tags.get("amenity") == "shelter" or tags.get("building") == "bunker":
            category = "bunkers_shelters"
        elif tags.get("amenity") == "parking" and tags.get("parking") == "underground":
            category = "underground_parking"
        else:
            continue

        locations.append({
            "name": name,
            "lat": el_lat,
            "lon": el_lon,
            "category": category,
            "distance_km": haversine(lat, lon, el_lat, el_lon)
        })

    return locations


async def get_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    """
    Get real road route using OSRM (Open Source Routing Machine).
    Returns distance, duration, and GeoJSON coordinates.
    """
    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise Exception("Routing service failed")

    route_data = response.json()["routes"][0]

    return {
        "distance_m": round(route_data["distance"], 1),
        "duration_s": round(route_data["duration"], 1),
        "geometry": route_data["geometry"]["coordinates"]  # [[lon, lat], ...]
    }


async def find_evacuation_routes(
    user_lat: float,
    user_lon: float,
    radius_km: float = 10.0,
    max_per_category: int = 2
):
    """
    Main logic: Find up to `max_per_category` nearest safe locations per category
    and compute real road routes to them.
    """
    safe_locations = await get_safe_locations(user_lat, user_lon, radius_km)

    # Sort by distance
    safe_locations.sort(key=lambda x: x["distance_km"])

    categories = {
        "hospitals": [],
        "bunkers_shelters": [],
        "underground_parking": []
    }

    for loc in safe_locations:
        category = loc["category"]
        if len(categories[category]) >= max_per_category:
            continue

        try:
            route = await get_route(user_lat, user_lon, loc["lat"], loc["lon"])
        except Exception as e:
            # Skip if routing fails for this location
            continue

        categories[category].append({
            "safe_location": loc["name"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "google_maps": f"https://www.google.com/maps?q={loc['lat']},{loc['lon']}",
            "distance_km": round(loc["distance_km"], 2),
            "route": route
        })

    alert_id = str(uuid.uuid4())

    return {
        "alert_id": alert_id,
        "results": {
            "user_position": {"lat": user_lat, "lon": user_lon},
            "search_radius_km": radius_km,
            "routes": categories
        }
    }


# Example usage when running the file directly
if __name__ == "__main__":
    async def main():
        # Example: Near central Berlin
        result = await find_evacuation_routes(
            user_lat=52.5200,
            user_lon=13.4050,
            radius_km=15.0
        )
        print(result)

    asyncio.run(main())