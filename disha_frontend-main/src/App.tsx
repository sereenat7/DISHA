import { useEffect, useState } from 'react';
import DisasterMap from './components/DisasterMap';
import AlertSystem from './components/AlertSystem';
import EvacuationRoutes from './components/EvacuationRoutes';
import SafetyRecommendations from './components/SafetyRecommendations';
import EmergencyDashboard from './components/EmergencyDashboard';
import { Location } from './types';
import { getUserLocation, calculateDistance, isInThreatZone, getSeverity } from './utils/geolocation';
import { mockHospitals, mockShelters, mockDisasterInfo } from './data/mockData';
import { Shield } from 'lucide-react';

function App() {
  const [userLocation, setUserLocation] = useState<Location | null>(null);
  const [isInDanger, setIsInDanger] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [distance, setDistance] = useState<number | null>(null);
  const [severity, setSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('low');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const threatZone = {
    center: { lat: 19.076, lon: 72.8777 },
    radiusKm: 5,
  };

  useEffect(() => {
    fetchUserLocation();
    const intervalId = setInterval(fetchUserLocation, 10000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (userLocation) {
      const inDanger = isInThreatZone(userLocation, threatZone.center, threatZone.radiusKm);
      setIsInDanger(inDanger);

      if (inDanger) {
        const dist = calculateDistance(userLocation, threatZone.center);
        setDistance(dist);
        setSeverity(getSeverity(dist, threatZone.radiusKm));
      } else {
        setDistance(null);
      }
    }
  }, [userLocation]);

  const fetchUserLocation = async () => {
    try {
      const location = await getUserLocation();
      setUserLocation(location);
      setLoading(false);
      setError(null);
    } catch (err) {
      console.error('Error getting location:', err);
      setError('Unable to get your location. Please enable location services.');
      setUserLocation({ lat: 19.076, lon: 72.8777 });
      setLoading(false);
    }
  };

  const handleMute = () => {
    setIsMuted(!isMuted);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      <AlertSystem
        isInDanger={isInDanger}
        severity={severity}
        distance={distance}
        onMute={handleMute}
        isMuted={isMuted}
      />

      <header className="bg-white shadow-md border-b-4 border-blue-500">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center space-x-3">
            <div className="bg-blue-500 p-2 rounded-lg">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">DISHA</h1>
              <p className="text-sm text-gray-600">Disaster Intelligence Safety & Help Application</p>
            </div>
          </div>
        </div>
      </header>

      {loading && (
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading your location...</p>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="bg-yellow-50 border-2 border-yellow-500 rounded-lg p-4">
            <p className="text-yellow-800">{error}</p>
            <p className="text-sm text-yellow-700 mt-2">Using demo location for testing purposes.</p>
          </div>
        </div>
      )}

      {!loading && (
        <main className="max-w-7xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            <div className="lg:col-span-2 space-y-4">
              <div className="h-[500px] lg:h-[600px]">
                <DisasterMap
                  userLocation={userLocation}
                  threatZone={threatZone}
                  hospitals={mockHospitals}
                  shelters={mockShelters}
                  evacuationRoutes={[]}
                />
              </div>
              {isInDanger && (
                <EvacuationRoutes userLocation={userLocation} isInDanger={isInDanger} />
              )}
            </div>

            <div className="space-y-4">
              <EmergencyDashboard
                isInDanger={isInDanger}
                severity={severity}
                distance={distance}
                affectedRadius={threatZone.radiusKm}
                disasterType={mockDisasterInfo.type}
                userLocation={userLocation}
              />
              <div className="h-[400px] lg:h-[500px]">
                <SafetyRecommendations
                  disasterType={mockDisasterInfo.type}
                  isInDanger={isInDanger}
                />
              </div>
            </div>
          </div>
        </main>
      )}

      <footer className="bg-white border-t-2 border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center">
          <p className="text-sm text-gray-600">
            DISHA - Your Safety is Our Priority | Emergency Hotline: 911
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
