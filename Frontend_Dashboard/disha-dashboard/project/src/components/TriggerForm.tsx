import { useState } from 'react';
import { Send, Loader2, AlertCircle } from 'lucide-react';
import { DisasterType, TriggerDisasterRequest, Disaster } from '../types';
import { api } from '../services/api';

interface TriggerFormProps {
  onDisasterTriggered: (disaster: Disaster) => void;
}

const DISASTER_TYPES: DisasterType[] = [
  "Flood",
  "Earthquake",
  "Fire",
  "Terrorist Attack",
  "Cyclone",
  "Tsunami",
  "Landslide",
  "Chemical Spill",
  "Nuclear Incident",
  "Volcanic Eruption",
  "Heatwave",
  "Biological Hazard",
];

export default function TriggerForm({ onDisasterTriggered }: TriggerFormProps) {
  const [formData, setFormData] = useState<TriggerDisasterRequest>({
    type: "Flood",
    latitude: 0,
    longitude: 0,
    radius_meters: 1000,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    if (formData.latitude < -90 || formData.latitude > 90) {
      setError('Latitude must be between -90 and 90');
      setLoading(false);
      return;
    }

    if (formData.longitude < -180 || formData.longitude > 180) {
      setError('Longitude must be between -180 and 180');
      setLoading(false);
      return;
    }

    if (formData.radius_meters < 100) {
      setError('Radius must be at least 100 meters');
      setLoading(false);
      return;
    }

    try {
      const response = await api.triggerDisaster(formData);

      const disaster: Disaster = {
        id: Date.now().toString(),
        ...formData,
        timestamp: new Date().toISOString(),
      };

      onDisasterTriggered(disaster);
      setSuccess(`${formData.type} triggered successfully at coordinates (${formData.latitude}, ${formData.longitude})`);

      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger disaster. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl shadow-2xl border border-slate-700 p-6">
      <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
        <AlertCircle className="text-red-400" size={24} />
        Trigger Disaster Event
      </h3>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Disaster Type
          </label>
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value as DisasterType })}
            className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
          >
            {DISASTER_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Latitude (-90 to 90)
            </label>
            <input
              type="number"
              step="any"
              value={formData.latitude}
              onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Longitude (-180 to 180)
            </label>
            <input
              type="number"
              step="any"
              value={formData.longitude}
              onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Radius (meters, min: 100)
          </label>
          <input
            type="number"
            min="100"
            value={formData.radius_meters}
            onChange={(e) => setFormData({ ...formData, radius_meters: parseInt(e.target.value) })}
            className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
            required
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
            <p className="text-red-200 text-sm">{error}</p>
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-4">
            <p className="text-green-200 text-sm">{success}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 disabled:from-slate-600 disabled:to-slate-600 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-red-500/30 disabled:shadow-none"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Triggering...
            </>
          ) : (
            <>
              <Send size={20} />
              Trigger Disaster
            </>
          )}
        </button>
      </form>
    </div>
  );
}
