import { useEffect, useMemo, useState, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { renderToStaticMarkup } from 'react-dom/server';
import { MapPin, Cross, Shield, AlertTriangle, ChevronDown, ChevronUp, Volume2, Navigation, Phone } from 'lucide-react';

interface Location {
  lat: number;
  lon: number;
}

interface SafeLocation {
  id: string;
  name: string;
  lat: number;
  lon: number;
  type: 'hospital' | 'shelter';
  distance_km?: number;
  routeGeometry?: number[][]; // [[lon, lat], ...]
}

interface ActiveDisaster {
  id: string;
  type: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  severity: number;
  created_at: string;
}

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
  const [activeDisasters, setActiveDisasters] = useState<ActiveDisaster[]>([]);
  const [isInDangerZone, setIsInDangerZone] = useState(false);
  const [safeLocations, setSafeLocations] = useState<SafeLocation[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<SafeLocation | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [hasTriggeredAlerts, setHasTriggeredAlerts] = useState(false);

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

  // Pre-warm AudioContext for alarm sound
  useEffect(() => {
    const initAudio = () => {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        const buffer = audioContextRef.current.createBuffer(1, 1, 22050);
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        source.start(0);
      }
    };

    initAudio();

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

  // Alarm sound when in danger
  useEffect(() => {
    if (!isInDangerZone || !audioContextRef.current) {
      if (beepIntervalRef.current) clearInterval(beepIntervalRef.current);
      if (oscillatorRef.current) {
        oscillatorRef.current.stop();
        oscillatorRef.current = null;
      }
      return;
    }

    if (!oscillatorRef.current) {
      oscillatorRef.current = audioContextRef.current.createOscillator();
      gainNodeRef.current = audioContextRef.current.createGain();

      oscillatorRef.current.connect(gainNodeRef.current);
      gainNodeRef.current.connect(audioContextRef.current.destination);

      oscillatorRef.current.type = 'sine';
      oscillatorRef.current.frequency.value = 950;
      gainNodeRef.current.gain.value = 0;

      oscillatorRef.current.start();
    }

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

  // Get user location
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

  // Poll active disasters
  useEffect(() => {
    if (!userLocation) return;

    const fetchActiveDisasters = async () => {
      try {
        const res = await fetch('https://disha-9gu7.onrender.com/disaster/active');
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        setActiveDisasters(data.active_disasters || []);
      } catch (err) {
        console.error('Failed to fetch disasters:', err);
        setActiveDisasters([]);
      }
    };

    fetchActiveDisasters();
    const interval = setInterval(fetchActiveDisasters, 5000);
    return () => clearInterval(interval);
  }, [userLocation]);

  // Danger detection + trigger alerts & evacuation
  useEffect(() => {
    if (!userLocation || activeDisasters.length === 0) {
      setIsInDangerZone(false);
      return;
    }

    const inDanger = activeDisasters.some((disaster) => {
      const distKm = calculateDistance(userLocation, { lat: disaster.latitude, lon: disaster.longitude });
      return distKm * 1000 <= disaster.radius_meters;
    });

    setIsInDangerZone(inDanger);

    if (inDanger && !hasTriggeredAlerts) {
      setHasTriggeredAlerts(true);

      const backendUrl = 'https://disha-backend-2b4i.onrender.com'; // Change to production URL when deploying

      // 1. Trigger CALL ALERTS to emergency contacts
      fetch(`${backendUrl}/api/alerts/trigger`, {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}), // Empty body as per your curl example
      })
        .then((res) => res.json())
        .then((data) => {
          console.log('Call alerts triggered:', data);
          if (data.status === 'completed') {
            // Optional: show a toast/notification in UI later
          }
        })
        .catch((err) => console.error('Call alert trigger failed:', err));

      // 2. Trigger evacuation routes
      fetch(`${backendUrl}/api/evacuation/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'web_user',
          user_lat: userLocation.lat,
          user_lon: userLocation.lon,
          radius_km: 10,
        }),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          const hospitals = data.evacuation_routes?.routes?.hospitals || [];
          const shelters = data.evacuation_routes?.routes?.bunkers_shelters || [];

          const allSafe: SafeLocation[] = [];

          hospitals.forEach((item: any, i: number) => {
            allSafe.push({
              id: `h-${Date.now()}-${i}`,
              name: item.safe_location || 'Hospital',
              lat: item.lat,
              lon: item.lon,
              type: 'hospital',
              distance_km: item.distance_km,
              routeGeometry: item.route?.geometry,
            });
          });

          shelters.forEach((item: any, i: number) => {
            allSafe.push({
              id: `s-${Date.now()}-${i}`,
              name: item.safe_location || 'Safe Shelter',
              lat: item.lat,
              lon: item.lon,
              type: 'shelter',
              distance_km: item.distance_km,
              routeGeometry: item.route?.geometry,
            });
          });

          allSafe.sort((a, b) => (a.distance_km || 999) - (b.distance_km || 999));
          setSafeLocations(allSafe.length > 0 ? allSafe : []);
        })
        .catch((err) => {
          console.error('Evacuation API failed:', err);
          setSafeLocations([]);
        });
    } else if (!inDanger && hasTriggeredAlerts) {
      // User left danger zone
      setHasTriggeredAlerts(false);
      setSafeLocations([]);
      setSelectedLocation(null);
    }
  }, [userLocation, activeDisasters, hasTriggeredAlerts]);

  // Selected route polyline (real road path)
  const selectedRouteCoords = useMemo<[number, number][]>(() => {
    if (!selectedLocation?.routeGeometry) return [];

    return selectedLocation.routeGeometry
      .filter((point): point is [number, number] => Array.isArray(point) && point.length === 2)
      .map(([lon, lat]) => [lat, lon] as [number, number]);
  }, [selectedLocation]);

  const center = userLocation || { lat: 19.0760, lon: 72.8777 };

  if (!userLocation) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 text-xl">
        Getting location...
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Top Banner */}
      <div className="absolute top-0 left-0 right-0 z-20 text-white text-center py-4 font-bold shadow-2xl flex items-center justify-center gap-3">
        {isInDangerZone ? (
          <div className="bg-gradient-to-r from-red-600 to-orange-600 w-full animate-pulse">
            <Volume2 className="animate-pulse inline" size={32} />
            <Phone className="animate-pulse inline ml-2" size={28} />
            DANGER ZONE ACTIVE - CALLS SENT
            <br />
            <span className="text-base">
              {activeDisasters.length} active threat{activeDisasters.length > 1 ? 's' : ''}
            </span>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-green-600 to-green-500 w-full">
            SAFE ZONE
            <br />
            <span className="text-base">No active threats</span>
          </div>
        )}
      </div>

      {/* Safe Locations Panel */}
      {isInDangerZone && safeLocations.length > 0 && (
        <div className="absolute top-24 right-4 z-20 bg-white rounded-2xl shadow-2xl w-72 max-h-[75vh] overflow-hidden flex flex-col">
          <div className="flex items-center justify-between p-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-t-2xl">
            <h3 className="font-bold text-base">Nearest Safe Locations ({safeLocations.length})</h3>
            <button onClick={() => setPanelOpen(!panelOpen)}>
              {panelOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>
          {panelOpen && (
            <div className="overflow-y-auto p-3 space-y-2 flex-1">
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
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{loc.type === 'hospital' ? '🏥' : '🏠'}</span>
                    <div className="flex-1">
                      <p className="font-semibold text-sm truncate">{loc.name}</p>
                      <p className="text-xs text-gray-600">
                        {(loc.distance_km || 0).toFixed(2)} km away
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AR Navigation Button */}
      {isInDangerZone && safeLocations.length > 0 && (
        <button
          onClick={() => {
            if (selectedLocation) {
              window.open('https://majestic-cactus-a3fab7.netlify.app/', '_blank');
            } else {
              alert('Please select a safe location first to start AR Navigation');
            }
          }}
          className="absolute bottom-6 left-6 z-20 px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-2xl flex items-center gap-3 transition-all hover:scale-105"
        >
          <Navigation size={28} />
          Start AR Navigation
        </button>
      )}

      <MapContainer center={[center.lat, center.lon]} zoom={14} className="w-full h-full">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapController center={center} />

        {/* Threat Circles */}
        {activeDisasters.map((disaster) => (
          <Circle
            key={disaster.id}
            center={[disaster.latitude, disaster.longitude]}
            radius={disaster.radius_meters}
            pathOptions={{
              color: '#991b1b',
              weight: 6,
              fillColor: '#ef4444',
              fillOpacity: 0.35,
            }}
          >
            <Popup>
              <strong>{disaster.type} Alert</strong>
              <br />
              Radius: {(disaster.radius_meters / 1000).toFixed(1)} km
              <br />
              Severity: {disaster.severity}
            </Popup>
          </Circle>
        ))}

        {/* User Marker */}
        <Marker position={[userLocation.lat, userLocation.lon]} icon={icons.user}>
          <Popup>Your Location</Popup>
        </Marker>

        {/* Safe Location Markers */}
        {safeLocations.map((loc) => (
          <Marker
            key={loc.id}
            position={[loc.lat, loc.lon]}
            icon={loc.type === 'hospital' ? icons.hospital : icons.shelter}
          >
            <Popup>
              <strong>{loc.name}</strong>
              <br />
              {loc.distance_km ? `${loc.distance_km.toFixed(2)} km away` : ''}
            </Popup>
          </Marker>
        ))}

        {/* Selected Real Route */}
        {selectedRouteCoords.length > 1 && (
          <Polyline
            positions={selectedRouteCoords}
            pathOptions={{
              color: '#16a34a',
              weight: 8,
              opacity: 0.9,
              dashArray: '10, 10',
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}