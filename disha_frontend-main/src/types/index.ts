export interface Location {
  lat: number;
  lon: number;
}

export interface Marker {
  id: string;
  lat: number;
  lon: number;
  type: 'hospital' | 'shelter' | 'user';
  name: string;
}

export interface ThreatZone {
  center: Location;
  radiusKm: number;
}

export interface EvacuationRoute {
  id: string;
  type: 'primary' | 'alternative';
  coordinates: [number, number][];
  destination: {
    name: string;
    lat: number;
    lon: number;
    distance: number;
    eta: number;
  };
}

export interface AlertState {
  isInDanger: boolean;
  isMuted: boolean;
  distance: number | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
}
