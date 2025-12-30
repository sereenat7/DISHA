import { useEffect, useState } from 'react';
import { Navigation, MapPin, Clock } from 'lucide-react';

interface Destination {
  name: string;
  lat: number;
  lon: number;
  distance_km: number;
  duration_min?: number;
}

interface EvacuationRoute {
  id: string;
  type: 'hospital' | 'shelter';
  destination: Destination;
}

interface EvacuationRoutesProps {
  userLocation: { lat: number; lon: number } | null;
  isInDanger: boolean;
}

export default function EvacuationRoutes({ userLocation, isInDanger }: EvacuationRoutesProps) {
  const [routes, setRoutes] = useState<EvacuationRoute[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isInDanger && userLocation) {
      fetchEvacuationRoutes();
    } else {
      setRoutes([]);
    }
  }, [isInDanger, userLocation]);

  const fetchEvacuationRoutes = async () => {
    if (!userLocation) return;

    setLoading(true);
    try {
      const response = await fetch('https://disha-backend-2b4i.onrender.com/api/evacuation/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'web_user',
          user_lat: userLocation.lat,
          user_lon: userLocation.lon,
          radius_km: 10,
        }),
      });

      if (!response.ok) throw new Error('API failed');

      const data = await response.json();

      const hospitals = data.evacuation_routes?.routes?.hospitals || [];
      const shelters = data.evacuation_routes?.routes?.bunkers_shelters || [];

      const allRoutes: EvacuationRoute[] = [];

      hospitals.forEach((h: any, i: number) => {
        allRoutes.push({
          id: `hospital-${i}`,
          type: 'hospital',
          destination: {
            name: h.safe_location || 'Hospital',
            lat: h.lat,
            lon: h.lon,
            distance_km: h.distance_km || 0,
            duration_min: h.route?.duration_s ? Math.round(h.route.duration_s / 60) : undefined,
          },
        });
      });

      shelters.forEach((s: any, i: number) => {
        allRoutes.push({
          id: `shelter-${i}`,
          type: 'shelter',
          destination: {
            name: s.safe_location || 'Safe Shelter',
            lat: s.lat,
            lon: s.lon,
            distance_km: s.distance_km || 0,
            duration_min: s.route?.duration_s ? Math.round(s.route.duration_s / 60) : undefined,
          },
        });
      });

      allRoutes.sort((a, b) => a.destination.distance_km - b.destination.distance_km);
      setRoutes(allRoutes.slice(0, 4)); // Show top 4 for clean layout
    } catch (error) {
      console.error('Failed to load safe routes:', error);
      setRoutes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigate = (lat: number, lon: number) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&travelmode=walking`;
    window.open(url, '_blank');
  };

  if (!isInDanger) return null;

  if (loading) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-40 px-4 pb-6 pointer-events-none">
        <div className="max-w-lg mx-auto pointer-events-auto">
          <div className="bg-white rounded-2xl shadow-2xl p-5 text-center">
            <div className="animate-spin rounded-full h-9 w-9 border-4 border-red-600 border-t-transparent mx-auto" />
            <p className="mt-3 text-gray-700 font-medium">Finding safe routes...</p>
          </div>
        </div>
      </div>
    );
  }

  if (routes.length === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 px-4 pb-6 pointer-events-none">
      <div className="max-w-lg mx-auto pointer-events-auto">
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Compact Header */}
          <div className="bg-red-600 text-white px-5 py-3 flex items-center justify-center gap-2">
            <span className="font-bold text-lg">Nearest Safe Zones</span>
          </div>

          {/* Clean List */}
          <div className="p-4 space-y-4">
            {routes.map((route, index) => (
              <div
                key={route.id}
                className={`rounded-xl p-4 ${
                  index === 0
                    ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-500'
                    : 'bg-gray-50'
                }`}
              >
                {/* Name + Type Badge */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <MapPin className="w-5 h-5 text-gray-600" />
                    <h4 className="font-semibold text-gray-900">{route.destination.name}</h4>
                  </div>
                  {index === 0 && (
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-green-100 text-green-700">
                      RECOMMENDED
                    </span>
                  )}
                </div>

                {/* Distance & Time */}
                <div className="flex gap-5 text-sm text-gray-600 mb-4">
                  <div className="flex items-center gap-1.5">
                    <Navigation className="w-4 h-4" />
                    <span>{route.destination.distance_km.toFixed(1)} km</span>
                  </div>
                  {route.destination.duration_min && (
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      <span>~{route.destination.duration_min} min</span>
                    </div>
                  )}
                </div>

                {/* Navigate Button */}
                <button
                  onClick={() => handleNavigate(route.destination.lat, route.destination.lon)}
                  className={`w-full py-3 rounded-lg font-bold text-white flex items-center justify-center gap-2 transition-all ${
                    index === 0
                      ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-md'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <Navigation className="w-5 h-5" />
                  Navigate with Google Maps
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}