import { useEffect, useMemo, useState, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { renderToStaticMarkup } from 'react-dom/server';
import { MapPin, Cross, Shield, AlertTriangle, ChevronDown, ChevronUp, Volume2 } from 'lucide-react';
import { Location } from '../types';

interface SafeLocation {
  id: string;
  name: string;
  lat: number;
  lon: number;
  type: 'hospital' | 'shelter';
  routeGeometry?: number[][]; // [[lon, lat], ...]
}

const THREAT_ZONE = {
  center: { lat: 19.1337, lon: 72.8611 } as Location,
  radiusKm: 5,
};

function calculateDistance(loc1: Location, loc2: Location): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(loc2.lat - loc1.lat);
  const dLon = toRad(loc2.lon - loc1.lon);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(loc1.lat)) * Math.cos(toRad(loc2.lat)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function createCustomIcon(IconComponent: React.FC<any>, color: string) {
  const svg = renderToStaticMarkup(
    <IconComponent size={24} strokeWidth={2} className="text-white drop-shadow-md" />
  );
  return L.divIcon({
    html: `
      <div class="relative flex items-center justify-center">
        <div class="absolute inset-0 rounded-full bg-${color}-500 blur-lg opacity-60 animate-ping"></div>
        <div class="relative w-10 h-10 rounded-full bg-${color}-600 shadow-xl border-2 border-white flex items-center justify-center">
          ${svg}
        </div>
      </div>
    `,
    className: 'custom-div-icon',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
}

function MapController({ center }: { center: Location }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.flyTo([center.lat, center.lon], 14, { duration: 1.5 });
    }
  }, [center.lat, center.lon, map]);
  return null;
}

export default function DisasterMap() {
  const [userLocation, setUserLocation] = useState<Location | null>(null);
  const [isInDangerZone, setIsInDangerZone] = useState(false);
  const [safeLocations, setSafeLocations] = useState<SafeLocation[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<SafeLocation | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const beepIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const icons = {
    user: useMemo(() => createCustomIcon(MapPin, 'blue'), []),
    hospital: useMemo(() => createCustomIcon(Cross, 'red'), []),
    shelter: useMemo(() => createCustomIcon(Shield, 'green'), []),
    threat: useMemo(() => createCustomIcon(AlertTriangle, 'red'), []),
  };

  // Critical: Pre-warm AudioContext on first mount to bypass autoplay policy
  useEffect(() => {
    const initAudio = () => {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        // Create silent buffer to "unlock" audio immediately
        const buffer = audioContextRef.current.createBuffer(1, 1, 22050);
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        source.start(0);
      }
    };

    // Try to unlock as early as possible
    initAudio();

    // Also unlock on any early interaction
    const unlock = () => initAudio();
    document.addEventListener('touchstart', unlock, { once: true });
    document.addEventListener('click', unlock, { once: true });
    document.addEventListener('keydown', unlock, { once: true });

    return () => {
      document.removeEventListener('touchstart', unlock);
      document.removeEventListener('click', unlock);
      document.removeEventListener('keydown', unlock);
    };
  }, []);

  // Start/stop buzzing alert based on danger zone
  useEffect(() => {
    if (!isInDangerZone || !audioContextRef.current) {
      // Stop sound
      if (beepIntervalRef.current) {
        clearInterval(beepIntervalRef.current);
        beepIntervalRef.current = null;
      }
      if (oscillatorRef.current) {
        oscillatorRef.current.stop();
        oscillatorRef.current = null;
      }
      if (gainNodeRef.current) {
        gainNodeRef.current.disconnect();
        gainNodeRef.current = null;
      }
      return;
    }

    // Start urgent buzzing sound
    if (!oscillatorRef.current) {
      oscillatorRef.current = audioContextRef.current.createOscillator();
      gainNodeRef.current = audioContextRef.current.createGain();

      oscillatorRef.current.connect(gainNodeRef.current);
      gainNodeRef.current.connect(audioContextRef.current.destination);

      oscillatorRef.current.type = 'sine';
      oscillatorRef.current.frequency.value = 950; // Very urgent high pitch
      gainNodeRef.current.gain.value = 0;

      oscillatorRef.current.start();
    }

    // Fast repeating beeps: BEEP-BEEP-BEEP (every 800ms)
    beepIntervalRef.current = setInterval(() => {
      if (gainNodeRef.current && audioContextRef.current) {
        const now = audioContextRef.current.currentTime;
        gainNodeRef.current.gain.cancelScheduledValues(now);
        gainNodeRef.current.gain.setValueAtTime(0.6, now);
        gainNodeRef.current.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
      }
    }, 800);

    return () => {
      if (beepIntervalRef.current) clearInterval(beepIntervalRef.current);
    };
  }, [isInDangerZone]);

  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => setUserLocation({ lat: 19.1200, lon: 72.8702 }),
        { enableHighAccuracy: true }
      );
    } else {
      setUserLocation({ lat: 19.1200, lon: 72.8702 });
    }
  }, []);

  useEffect(() => {
    if (!userLocation) return;

    const dist = calculateDistance(userLocation, THREAT_ZONE.center);
    const inDanger = dist <= THREAT_ZONE.radiusKm;
    setIsInDangerZone(inDanger);

    if (inDanger) {
      // Trigger emergency alerts
      fetch('http://127.0.0.1:8000/api/alerts/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'web_emergency',
          user_lat: userLocation.lat,
          user_lon: userLocation.lon,
        }),
      }).catch(() => {});

      // Fetch evacuation routes
      fetch('http://127.0.0.1:8000/api/evacuation/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'web_test',
          user_lat: userLocation.lat,
          user_lon: userLocation.lon,
          radius_km: 10,
        }),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error('Evacuation API failed');
          return res.json();
        })
        .then((data) => {
          const routes = data?.evacuation_routes?.routes || {};
          const locations: SafeLocation[] = [];

          if (Array.isArray(routes.hospitals)) {
            routes.hospitals.forEach((item: any, i: number) => {
              if (typeof item.lat === 'number' && typeof item.lon === 'number') {
                locations.push({
                  id: `h-${i}`,
                  name: item.safe_location || 'Hospital',
                  lat: item.lat,
                  lon: item.lon,
                  type: 'hospital',
                  routeGeometry: Array.isArray(item.route?.geometry)
                    ? item.route.geometry.filter((p: any) => Array.isArray(p) && p.length === 2)
                    : [],
                });
              }
            });
          }

          const shelterArrays = [
            routes.bunkers_shelters || [],
            routes.underground_parking || [],
          ];

          shelterArrays.forEach((arr) => {
            if (Array.isArray(arr)) {
              arr.forEach((item: any, i: number) => {
                if (typeof item.lat === 'number' && typeof item.lon === 'number') {
                  locations.push({
                    id: `s-${Date.now()}-${i}`,
                    name: item.safe_location || 'Shelter',
                    lat: item.lat,
                    lon: item.lon,
                    type: 'shelter',
                    routeGeometry: Array.isArray(item.route?.geometry)
                      ? item.route.geometry.filter((p: any) => Array.isArray(p) && p.length === 2)
                      : [],
                  });
                }
              });
            }
          });

          setSafeLocations(locations);
          setError(null);
        })
        .catch((err) => {
          console.error('Evacuation API error:', err);
          setError('Failed to load safe locations');
          setSafeLocations([]);
        });
    } else {
      setSafeLocations([]);
    }
  }, [userLocation]);

  const selectedRouteCoords = useMemo<[number, number][]>(() => {
    if (!selectedLocation?.routeGeometry || !Array.isArray(selectedLocation.routeGeometry)) {
      return [];
    }

    return selectedLocation.routeGeometry
      .filter((point): point is [number, number] => 
        Array.isArray(point) && 
        point.length === 2 && 
        typeof point[0] === 'number' && 
        typeof point[1] === 'number' &&
        !isNaN(point[0]) && !isNaN(point[1])
      )
      .map((point) => [point[1], point[0]] as [number, number]);
  }, [selectedLocation]);

  const center = userLocation || THREAT_ZONE.center;

  if (!userLocation) {
    return <div className="w-full h-full flex items-center justify-center text-gray-500 text-xl">Getting your location...</div>;
  }

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Top Danger Banner */}
      <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-r from-red-600 to-orange-600 text-white text-center py-4 font-bold shadow-2xl flex items-center justify-center gap-3">
        <Volume2 className="animate-pulse" size={32} />
        DANGER ALERT — ACTIVE
        <br />
        <span className="text-base">
          Distance: {calculateDistance(userLocation, THREAT_ZONE.center).toFixed(1)} km from threat center
        </span>
      </div>

      {/* Error Message */}
      {error && (
        <div className="absolute top-24 left-4 z-20 bg-red-100 text-red-700 px-4 py-3 rounded-lg shadow-lg">
          {error}
        </div>
      )}

      {/* Safe Locations Panel */}
      {safeLocations.length > 0 && (
        <div className="absolute top-24 right-4 z-20 bg-white rounded-2xl shadow-2xl w-64 max-h-[65vh] overflow-hidden flex flex-col">
          <div className="flex items-center justify-between p-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-t-2xl">
            <h3 className="font-bold text-base">Safe Locations ({safeLocations.length})</h3>
            <button onClick={() => setPanelOpen(!panelOpen)}>
              {panelOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>
          {panelOpen && (
            <div className="overflow-y-auto p-3 space-y-2">
              {safeLocations.map((loc) => (
                <div
                  key={loc.id}
                  onClick={() => setSelectedLocation(selectedLocation?.id === loc.id ? null : loc)}
                  className={`p-3 rounded-lg border-2 cursor-pointer transition-all shadow-sm ${
                    selectedLocation?.id === loc.id
                      ? 'border-green-500 bg-green-50 shadow-lg scale-105'
                      : 'border-gray-200 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{loc.type === 'hospital' ? '🏥' : '🏠'}</span>
                    <div>
                      <p className="font-semibold text-sm truncate">{loc.name}</p>
                      <p className="text-xs text-gray-600">{loc.lat.toFixed(4)}, {loc.lon.toFixed(4)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <MapContainer center={[center.lat, center.lon]} zoom={14} className="w-full h-full">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapController center={center} />

        <Circle
          center={[THREAT_ZONE.center.lat, THREAT_ZONE.center.lon]}
          radius={THREAT_ZONE.radiusKm * 1000}
          pathOptions={{
            color: '#991b1b',
            weight: 6,
            fillColor: '#ef4444',
            fillOpacity: 0.35,
          }}
        />

        <Marker position={[userLocation.lat, userLocation.lon]} icon={icons.user}>
          <Popup>Your Location</Popup>
        </Marker>

        {safeLocations.map((loc) => (
          <Marker
            key={loc.id}
            position={[loc.lat, loc.lon]}
            icon={loc.type === 'hospital' ? icons.hospital : icons.shelter}
          >
            <Popup>{loc.name}</Popup>
          </Marker>
        ))}

        {selectedRouteCoords.length > 1 && (
          <Polyline
            positions={selectedRouteCoords}
            pathOptions={{
              color: '#16a34a',
              weight: 10,
              opacity: 1,
              dashArray: '15, 10',
              className: 'animate-pulse',
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}