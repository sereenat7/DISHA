import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Disaster } from '../types';
import { Map as MapIcon, Satellite } from 'lucide-react';

interface MapContainerProps {
  disasters: Disaster[];
}

export default function MapContainer({ disasters }: MapContainerProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Map<string, { marker: L.Marker; circle: L.Circle }>>(new Map());
  const [mapType, setMapType] = useState<'street' | 'satellite'>('street');
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [20, 0],
      zoom: 2,
      zoomControl: true,
      attributionControl: true,
    });

    const streetTileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    });

    streetTileLayer.addTo(map);
    tileLayerRef.current = streetTileLayer;
    mapRef.current = map;

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          map.setView([position.coords.latitude, position.coords.longitude], 6);
        },
        () => {
          map.setView([20, 0], 2);
        }
      );
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !tileLayerRef.current) return;

    tileLayerRef.current.remove();

    if (mapType === 'street') {
      tileLayerRef.current = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapRef.current);
    } else {
      tileLayerRef.current = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          attribution: 'Tiles © Esri',
          maxZoom: 19,
        }
      ).addTo(mapRef.current);
    }
  }, [mapType]);

  useEffect(() => {
    if (!mapRef.current) return;

    const currentMarkerIds = new Set(disasters.map((d) => d.id));
    const existingMarkerIds = new Set(markersRef.current.keys());

    existingMarkerIds.forEach((id) => {
      if (!currentMarkerIds.has(id)) {
        const layers = markersRef.current.get(id);
        if (layers) {
          mapRef.current?.removeLayer(layers.marker);
          mapRef.current?.removeLayer(layers.circle);
          markersRef.current.delete(id);
        }
      }
    });

    disasters.forEach((disaster) => {
      if (!markersRef.current.has(disaster.id)) {
        const redIcon = L.divIcon({
          className: 'custom-disaster-marker',
          html: `
            <div style="
              background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
              width: 32px;
              height: 32px;
              border-radius: 50% 50% 50% 0;
              border: 3px solid white;
              box-shadow: 0 4px 12px rgba(239, 68, 68, 0.6);
              transform: rotate(-45deg);
              display: flex;
              align-items: center;
              justify-content: center;
            ">
              <div style="
                transform: rotate(45deg);
                color: white;
                font-size: 16px;
                font-weight: bold;
              ">!</div>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32],
        });

        const marker = L.marker([disaster.latitude, disaster.longitude], {
          icon: redIcon,
        }).addTo(mapRef.current);

        const popupContent = `
          <div style="font-family: system-ui; padding: 8px;">
            <h3 style="margin: 0 0 8px 0; font-weight: 600; color: #1e293b; font-size: 16px;">${disaster.type}</h3>
            <p style="margin: 4px 0; color: #64748b; font-size: 13px;">
              <strong>Location:</strong> ${disaster.latitude.toFixed(4)}, ${disaster.longitude.toFixed(4)}
            </p>
            <p style="margin: 4px 0; color: #64748b; font-size: 13px;">
              <strong>Radius:</strong> ${disaster.radius_meters.toLocaleString()} meters
            </p>
            <p style="margin: 4px 0; color: #64748b; font-size: 13px;">
              <strong>Time:</strong> ${new Date(disaster.timestamp).toLocaleString()}
            </p>
          </div>
        `;

        marker.bindPopup(popupContent);

        const circle = L.circle([disaster.latitude, disaster.longitude], {
          color: '#ef4444',
          fillColor: '#f87171',
          fillOpacity: 0.25,
          radius: disaster.radius_meters,
          weight: 2,
        }).addTo(mapRef.current);

        markersRef.current.set(disaster.id, { marker, circle });

        mapRef.current.setView([disaster.latitude, disaster.longitude], 10);
      }
    });
  }, [disasters]);

  const toggleMapType = () => {
    setMapType((prev) => (prev === 'street' ? 'satellite' : 'street'));
  };

  return (
    <div className="relative h-full w-full rounded-xl overflow-hidden shadow-2xl border border-slate-700">
      <div ref={mapContainerRef} className="h-full w-full" />

      <button
        onClick={toggleMapType}
        className="absolute top-4 right-4 z-[1000] flex items-center gap-2 px-4 py-2 bg-slate-800/90 backdrop-blur-sm hover:bg-slate-700/90 border border-slate-600 text-white rounded-lg transition-all duration-200 shadow-lg"
      >
        {mapType === 'street' ? (
          <>
            <Satellite size={18} />
            <span className="font-medium">Satellite View</span>
          </>
        ) : (
          <>
            <MapIcon size={18} />
            <span className="font-medium">Street View</span>
          </>
        )}
      </button>

      {disasters.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-slate-800/90 backdrop-blur-sm px-6 py-4 rounded-lg border border-slate-600 shadow-xl">
            <p className="text-slate-300 text-center">
              No disasters triggered yet. Use the form to trigger one.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
