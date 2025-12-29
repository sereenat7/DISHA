from fastapi import FastAPI, HTTPException
import httpx
import uuid
import math

app = FastAPI(title="Dynamic OSM Evacuation Backend", version="1.0")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# ----------------------------
# UTILS
# ----------------------------


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# ----------------------------
# FETCH SAFE LOCATIONS
# ----------------------------

async def get_safe_locations(lat, lon, radius_km):
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

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(OVERPASS_URL, data=query)

    if res.status_code != 200 or not res.text.strip():
        return []

    data = res.json()
    locations = []

    for el in data.get("elements", []):
        lat_ = el.get("lat")
        lon_ = el.get("lon")
        if not lat_ or not lon_:
            continue

        tags = el.get("tags", {})
        name = tags.get("name", "Safe Location")

        if tags.get("amenity") == "hospital":
            category = "hospitals"
        elif tags.get("amenity") == "shelter" or tags.get("building") == "bunker":
            category = "bunkers_shelters"
        elif tags.get("amenity") == "parking":
            category = "underground_parking"
        else:
            continue

        locations.append({
            "name": name,
            "lat": lat_,
            "lon": lon_,
            "category": category,
            "distance": haversine(lat, lon, lat_, lon_)
        })

    return locations


# ----------------------------
# ROUTING (REAL ROADS)
# ----------------------------

async def get_route(start_lat, start_lon, end_lat, end_lon):
    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(url)

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Routing failed")

    route = res.json()["routes"][0]

    return {
        "distance_m": round(route["distance"], 1),
        "duration_s": round(route["duration"], 1),
        "geometry": route["geometry"]["coordinates"]
    }


# ----------------------------
# MAIN API
# ----------------------------

@app.post("/disaster/trigger")
async def trigger_disaster(
    user_id: str,
    user_lat: float,
    user_lon: float,
    radius_km: float
):
    safe_locations = await get_safe_locations(user_lat, user_lon, radius_km)

    categories = {
        "hospitals": [],
        "bunkers_shelters": [],
        "underground_parking": []
    }

    # sort by distance
    safe_locations.sort(key=lambda x: x["distance"])

    for loc in safe_locations:
        if len(categories[loc["category"]]) >= 2:
            continue

        route = await get_route(
            user_lat, user_lon,
            loc["lat"], loc["lon"]
        )

        categories[loc["category"]].append({
            "safe_location": loc["name"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "google_maps": f"https://www.google.com/maps?q={loc['lat']},{loc['lon']}",
            "route": route
        })

    return {
        "alert_id": str(uuid.uuid4()),
        "affected_users": 1,
        "results": [
            {
                "user_id": user_id,
                "routes": categories
            }
        ]
    }
