import { CheckCircle, AlertCircle, Phone, Share2, Heart, MapPin } from 'lucide-react';
import { Location } from '../types';

interface EmergencyDashboardProps {
  isInDanger: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  distance: number | null;
  affectedRadius: number;
  disasterType: string;
  userLocation: Location | null;
}

export default function EmergencyDashboard({
  isInDanger,
  severity,
  distance,
  affectedRadius,
  disasterType,
  userLocation,
}: EmergencyDashboardProps) {
  const handleImSafe = () => {
    alert('Your safety status has been shared with emergency contacts!');
  };

  const handleNeedHelp = () => {
    alert('Emergency services have been notified of your location!');
  };

  const handleCall911 = () => {
    window.location.href = 'tel:911';
  };

  const handleShareLocation = () => {
    if (userLocation && navigator.share) {
      navigator
        .share({
          title: 'My Emergency Location',
          text: `I'm at an emergency location. Coordinates: ${userLocation.lat}, ${userLocation.lon}`,
          url: `https://www.google.com/maps?q=${userLocation.lat},${userLocation.lon}`,
        })
        .catch((error) => console.error('Error sharing:', error));
    } else if (userLocation) {
      const url = `https://www.google.com/maps?q=${userLocation.lat},${userLocation.lon}`;
      navigator.clipboard.writeText(url);
      alert('Location link copied to clipboard!');
    }
  };

  const statusColor = isInDanger ? 'bg-red-500' : 'bg-green-500';
  const statusText = isInDanger ? 'DANGER' : 'SAFE';
  const StatusIcon = isInDanger ? AlertCircle : CheckCircle;

  const severityColors = {
    low: 'text-yellow-600',
    medium: 'text-orange-600',
    high: 'text-red-600',
    critical: 'text-red-700',
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 space-y-4">
      <div className="text-center">
        <div
          className={`${statusColor} text-white rounded-lg p-4 mb-4 shadow-md ${
            isInDanger ? 'pulse-animation' : ''
          }`}
        >
          <StatusIcon className="w-12 h-12 mx-auto mb-2" />
          <h2 className="text-2xl font-bold">{statusText}</h2>
          <p className="text-sm mt-1">Status: {isInDanger ? 'Active Threat' : 'No Threats'}</p>
        </div>
      </div>

      {isInDanger && (
        <div className="bg-red-50 border-2 border-red-500 rounded-lg p-3">
          <h3 className="font-bold text-red-800 mb-2">Active Threat Information</h3>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-700">Type:</span>
              <span className="font-semibold text-gray-900">{disasterType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700">Severity:</span>
              <span className={`font-semibold ${severityColors[severity]} uppercase`}>
                {severity}
              </span>
            </div>
            {distance !== null && (
              <div className="flex justify-between">
                <span className="text-gray-700">Distance from center:</span>
                <span className="font-semibold text-gray-900">{distance.toFixed(2)} km</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-700">Affected radius:</span>
              <span className="font-semibold text-gray-900">{affectedRadius} km</span>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="font-bold text-gray-800 text-sm mb-2">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleImSafe}
            className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-3 rounded-lg transition-colors flex items-center justify-center space-x-2 text-sm"
          >
            <Heart className="w-4 h-4" />
            <span>I'm Safe</span>
          </button>
          <button
            onClick={handleNeedHelp}
            className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2 px-3 rounded-lg transition-colors flex items-center justify-center space-x-2 text-sm"
          >
            <AlertCircle className="w-4 h-4" />
            <span>Need Help</span>
          </button>
          <button
            onClick={handleCall911}
            className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-3 rounded-lg transition-colors flex items-center justify-center space-x-2 text-sm"
          >
            <Phone className="w-4 h-4" />
            <span>Call 911</span>
          </button>
          <button
            onClick={handleShareLocation}
            className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded-lg transition-colors flex items-center justify-center space-x-2 text-sm"
          >
            <Share2 className="w-4 h-4" />
            <span>Share Location</span>
          </button>
        </div>
      </div>

      <div className="bg-blue-50 border-2 border-blue-500 rounded-lg p-3">
        <div className="flex items-start space-x-2">
          <MapPin className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <p className="font-semibold text-blue-800 text-sm">Your Location</p>
            {userLocation ? (
              <p className="text-xs text-gray-600">
                {userLocation.lat.toFixed(4)}, {userLocation.lon.toFixed(4)}
              </p>
            ) : (
              <p className="text-xs text-gray-600">Acquiring location...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
