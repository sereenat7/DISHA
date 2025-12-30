import { Location } from '../types';

export function calculateDistance(
  point1: Location,
  point2: Location
): number {
  const R = 6371;
  const dLat = toRad(point2.lat - point1.lat);
  const dLon = toRad(point2.lon - point1.lon);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(point1.lat)) *
      Math.cos(toRad(point2.lat)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function toRad(degrees: number): number {
  return degrees * (Math.PI / 180);
}

export function isInThreatZone(
  userLocation: Location,
  threatCenter: Location,
  radiusKm: number
): boolean {
  const distance = calculateDistance(userLocation, threatCenter);
  return distance <= radiusKm;
}

export function getSeverity(
  distance: number,
  radiusKm: number
): 'low' | 'medium' | 'high' | 'critical' {
  const percentage = (distance / radiusKm) * 100;

  if (percentage <= 25) return 'critical';
  if (percentage <= 50) return 'high';
  if (percentage <= 75) return 'medium';
  return 'low';
}

export function getUserLocation(): Promise<Location> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        });
      },
      (error) => {
        reject(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    );
  });
}
