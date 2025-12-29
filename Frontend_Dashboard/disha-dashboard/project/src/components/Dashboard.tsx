import { Activity, AlertTriangle, MapPin, TrendingUp } from 'lucide-react';
import { Disaster } from '../types';

interface DashboardProps {
  disasters: Disaster[];
}

export default function Dashboard({ disasters }: DashboardProps) {
  const stats = [
    {
      label: 'Total Disasters',
      value: disasters.length,
      icon: AlertTriangle,
      color: 'from-red-500 to-orange-500',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
    },
    {
      label: 'Active Events',
      value: disasters.length,
      icon: Activity,
      color: 'from-blue-500 to-cyan-500',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/30',
    },
    {
      label: 'Locations Monitored',
      value: new Set(disasters.map(d => `${d.latitude},${d.longitude}`)).size,
      icon: MapPin,
      color: 'from-green-500 to-emerald-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
    },
    {
      label: 'Coverage Area (km²)',
      value: Math.round(disasters.reduce((sum, d) => sum + (Math.PI * Math.pow(d.radius_meters / 1000, 2)), 0)),
      icon: TrendingUp,
      color: 'from-yellow-500 to-amber-500',
      bgColor: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/30',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-600 to-cyan-600 rounded-xl p-8 shadow-2xl">
        <h2 className="text-3xl font-bold text-white mb-2">Welcome to Disaster Admin Dashboard</h2>
        <p className="text-blue-100">Monitor, manage, and respond to disaster events in real-time</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className={`${stat.bgColor} ${stat.borderColor} border backdrop-blur-sm rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 bg-gradient-to-br ${stat.color} rounded-lg shadow-lg`}>
                  <Icon className="text-white" size={24} />
                </div>
              </div>
              <p className="text-slate-400 text-sm mb-1">{stat.label}</p>
              <p className="text-white text-3xl font-bold">{stat.value.toLocaleString()}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl shadow-2xl border border-slate-700 p-6">
          <h3 className="text-xl font-bold text-white mb-4">Recent Activity</h3>
          <div className="space-y-3 max-h-[300px] overflow-y-auto custom-scrollbar">
            {disasters.length === 0 ? (
              <p className="text-slate-400 text-center py-8">No disasters triggered yet</p>
            ) : (
              disasters.slice().reverse().slice(0, 5).map((disaster) => (
                <div
                  key={disaster.id}
                  className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg border border-slate-600/50"
                >
                  <div className="p-2 bg-red-500/20 rounded-lg">
                    <AlertTriangle className="text-red-400" size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium">{disaster.type}</p>
                    <p className="text-slate-400 text-sm">
                      {disaster.latitude.toFixed(4)}, {disaster.longitude.toFixed(4)}
                    </p>
                    <p className="text-slate-500 text-xs mt-1">
                      {new Date(disaster.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl shadow-2xl border border-slate-700 p-6">
          <h3 className="text-xl font-bold text-white mb-4">System Status</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
              <span className="text-slate-300">API Status</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-medium">Operational</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
              <span className="text-slate-300">Map Services</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-medium">Online</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
              <span className="text-slate-300">News Feed</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-medium">Active</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
              <span className="text-slate-300">Last Update</span>
              <span className="text-slate-400 font-medium">{new Date().toLocaleTimeString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
