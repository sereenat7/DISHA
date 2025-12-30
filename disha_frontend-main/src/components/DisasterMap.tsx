import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Cross, Shield } from 'lucide-react';
import { Location, Marker as MarkerType, EvacuationRoute } from '../types';

interface DisasterMapProps {
  userLocation: Location | null;
  threatZone: { center: Location; radiusKm: number } | null;
  hospitals: MarkerType[];
  shelters: MarkerType[];
  evacuationRoutes: EvacuationRoute[];
}

function createCustomIcon(color: string, IconComponent: typeof MapPin) {
  return L.divIcon({
    className: 'custom-icon',
    html: `
      <div class="relative">
        <div class="absolute inset-0 bg-${color}-500 rounded-full blur-md opacity-50 pulse-animation"></div>
        <div class="relative bg-${color}-500 rounded-full p-2 shadow-lg">
          ${renderIconSvg(IconComponent, color)}
        </div>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
}

function renderIconSvg(IconComponent: typeof MapPin, color: string): string {
  const iconMap: Record<string, string> = {
    blue: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`,
    red: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2a2 2 0 0 0-2 2v5H4a2 2 0 0 0-2 2v2c0 1.1.9 2 2 2h5v5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-5h5a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-5V4a2 2 0 0 0-2-2h-2z"/></svg>`,
    green: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  };
  return iconMap[color] || iconMap.blue;
}

function MapController({ center }: { center: Location }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView([center.lat, center.lon], map.getZoom());
    }
  }, [center, map]);
  return null;
}

export default function DisasterMap({
  userLocation,
  threatZone,
  hospitals,
  shelters,
  evacuationRoutes,
}: DisasterMapProps) {
  const userIcon = useMemo(() => createCustomIcon('blue', MapPin), []);
  const hospitalIcon = useMemo(() => createCustomIcon('red', Cross), []);
  const shelterIcon = useMemo(() => createCustomIcon('green', Shield), []);

  const defaultCenter: Location = userLocation || { lat: 19.076, lon: 72.8777 };

  return (
    <div className="w-full h-full rounded-lg overflow-hidden shadow-lg">
      <MapContainer
        center={[defaultCenter.lat, defaultCenter.lon]}
        zoom={13}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {userLocation && <MapController center={userLocation} />}

        {threatZone && (
          <>
            <Circle
              center={[threatZone.center.lat, threatZone.center.lon]}
              radius={threatZone.radiusKm * 1000}
              pathOptions={{
                color: '#ef4444',
                fillColor: '#ef4444',
                fillOpacity: 0.2,
                weight: 3,
              }}
            />
            <Circle
              center={[threatZone.center.lat, threatZone.center.lon]}
              radius={threatZone.radiusKm * 1000}
              pathOptions={{
                color: '#ef4444',
                fillColor: 'transparent',
                fillOpacity: 0,
                weight: 2,
                dashArray: '10, 10',
                className: 'pulse-animation',
              }}
            />
          </>
        )}

        {userLocation && (
          <Marker position={[userLocation.lat, userLocation.lon]} icon={userIcon}>
            <Popup>
              <div className="text-center">
                <p className="font-semibold">Your Location</p>
                <p className="text-xs text-gray-600">
                  {userLocation.lat.toFixed(4)}, {userLocation.lon.toFixed(4)}
                </p>
              </div>
            </Popup>
          </Marker>
        )}

        {hospitals.map((hospital) => (
          <Marker
            key={hospital.id}
            position={[hospital.lat, hospital.lon]}
            icon={hospitalIcon}
          >
            <Popup>
              <div className="text-center">
                <p className="font-semibold text-red-600">{hospital.name}</p>
                <p className="text-xs text-gray-600">Emergency Medical Facility</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {shelters.map((shelter) => (
          <Marker
            key={shelter.id}
            position={[shelter.lat, shelter.lon]}
            icon={shelterIcon}
          >
            <Popup>
              <div className="text-center">
                <p className="font-semibold text-green-600">{shelter.name}</p>
                <p className="text-xs text-gray-600">Emergency Shelter</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {evacuationRoutes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.coordinates}
            pathOptions={{
              color: route.type === 'primary' ? '#22c55e' : '#3b82f6',
              weight: 4,
              opacity: 0.7,
            }}
          />
        ))}
      </MapContainer>
    </div>
  );
}
