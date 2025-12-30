import { useEffect, useState } from 'react';
import { Navigation, MapPin, Clock, Route } from 'lucide-react';
import { EvacuationRoute, Location } from '../types';

interface EvacuationRoutesProps {
  userLocation: Location | null;
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
      const response = await fetch('http://localhost:8000/api/evacuation/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'user123',
          user_lat: userLocation.lat,
          user_lon: userLocation.lon,
          radius_km: 10,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.routes) {
          setRoutes(data.routes);
        }
      } else {
        generateMockRoutes();
      }
    } catch (error) {
      console.error('Failed to fetch evacuation routes:', error);
      generateMockRoutes();
    } finally {
      setLoading(false);
    }
  };

  const generateMockRoutes = () => {
    if (!userLocation) return;

    const mockRoutes: EvacuationRoute[] = [
      {
        id: 'route1',
        type: 'primary',
        coordinates: [
          [userLocation.lat, userLocation.lon],
          [userLocation.lat + 0.01, userLocation.lon + 0.01],
          [userLocation.lat + 0.02, userLocation.lon + 0.015],
          [userLocation.lat + 0.03, userLocation.lon + 0.02],
        ],
        destination: {
          name: 'Community Shelter A',
          lat: userLocation.lat + 0.03,
          lon: userLocation.lon + 0.02,
          distance: 3.2,
          eta: 8,
        },
      },
      {
        id: 'route2',
        type: 'alternative',
        coordinates: [
          [userLocation.lat, userLocation.lon],
          [userLocation.lat - 0.005, userLocation.lon + 0.015],
          [userLocation.lat - 0.01, userLocation.lon + 0.025],
          [userLocation.lat - 0.015, userLocation.lon + 0.03],
        ],
        destination: {
          name: 'Emergency Bunker B',
          lat: userLocation.lat - 0.015,
          lon: userLocation.lon + 0.03,
          distance: 4.1,
          eta: 12,
        },
      },
    ];

    setRoutes(mockRoutes);
  };

  const handleNavigate = (destination: { lat: number; lon: number; name: string }) => {
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${destination.lat},${destination.lon}`;
    window.open(googleMapsUrl, '_blank');
  };

  if (!isInDanger || routes.length === 0) return null;

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 space-y-3">
      <div className="flex items-center space-x-2 mb-3">
        <Route className="w-5 h-5 text-blue-600" />
        <h3 className="font-bold text-lg text-gray-800">Evacuation Routes</h3>
      </div>

      {loading ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-sm text-gray-600 mt-2">Finding safe routes...</p>
        </div>
      ) : (
        <div className="space-y-3">
          {routes.map((route) => (
            <div
              key={route.id}
              className={`border-2 ${
                route.type === 'primary' ? 'border-green-500' : 'border-blue-500'
              } rounded-lg p-3 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span
                      className={`px-2 py-1 rounded text-xs font-semibold ${
                        route.type === 'primary'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {route.type === 'primary' ? 'PRIMARY ROUTE' : 'ALTERNATIVE'}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-gray-700">
                    <MapPin className="w-4 h-4" />
                    <span className="font-semibold">{route.destination.name}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                <div className="flex items-center space-x-1">
                  <Navigation className="w-4 h-4" />
                  <span>{route.destination.distance.toFixed(1)} km</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{route.destination.eta} min</span>
                </div>
              </div>

              <button
                onClick={() => handleNavigate(route.destination)}
                className={`w-full ${
                  route.type === 'primary'
                    ? 'bg-green-500 hover:bg-green-600'
                    : 'bg-blue-500 hover:bg-blue-600'
                } text-white font-semibold py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2`}
              >
                <Navigation className="w-4 h-4" />
                <span>Navigate Now</span>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
