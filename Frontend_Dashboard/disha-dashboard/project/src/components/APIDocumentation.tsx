import React, { useState } from 'react';
import { Copy, Check, ChevronDown, ChevronRight, Code, Zap, Shield, Globe } from 'lucide-react';

const APIDocumentation = () => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [expandedEndpoint, setExpandedEndpoint] = useState<string | null>('alerts-trigger');
  const [selectedLanguage, setSelectedLanguage] = useState('curl');

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const baseUrl = 'https://your-api-domain.com';

  const endpoints = [
    {
      id: 'alerts-trigger',
      category: 'ADMIN',
      method: 'POST',
      path: '/api/alerts/trigger',
      title: 'Trigger Emergency Alerts',
      description: 'Send emergency alerts via SMS and voice calls to all registered contacts in the system.',
      request: null,
      response: {
        status: 'completed',
        message: 'Alerts sent successfully',
        total_contacts: 3,
        timestamp: '2025-01-01T10:30:00Z',
        results: [
          {
            phone: '+918850755760',
            total_calls: 1,
            successful_calls: 1,
            sms_sent: true
          }
        ]
      },
      codes: [200, 500],
      codeExamples: {
        curl: `curl -X POST ${baseUrl}/api/alerts/trigger \\
  -H "Content-Type: application/json"`,
        javascript: `fetch('${baseUrl}/api/alerts/trigger', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log(data));`,
        python: `import requests

response = requests.post(
    '${baseUrl}/api/alerts/trigger'
)
print(response.json())`
      }
    },
    {
      id: 'evacuation-trigger',
      category: 'ADMIN',
      method: 'POST',
      path: '/api/evacuation/trigger',
      title: 'Calculate Evacuation Routes',
      description: 'Compute optimal evacuation routes to safe locations based on user coordinates and search radius.',
      request: {
        user_id: 'user_123',
        user_lat: 19.0760,
        user_lon: 72.8777,
        radius_km: 10.0
      },
      response: {
        status: 'success',
        user_id: 'user_123',
        alert_id: 'alert_456',
        timestamp: '2025-01-01T10:30:00Z',
        evacuation_routes: [
          {
            category: 'hospital',
            name: 'City General Hospital',
            distance_km: 2.5,
            duration_min: 8
          }
        ]
      },
      codes: [200, 400, 500],
      codeExamples: {
        curl: `curl -X POST ${baseUrl}/api/evacuation/trigger \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": "user_123",
    "user_lat": 19.0760,
    "user_lon": 72.8777,
    "radius_km": 10.0
  }'`,
        javascript: `fetch('${baseUrl}/api/evacuation/trigger', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: 'user_123',
    user_lat: 19.0760,
    user_lon: 72.8777,
    radius_km: 10.0
  })
})
.then(res => res.json())
.then(data => console.log(data));`,
        python: `import requests

data = {
    'user_id': 'user_123',
    'user_lat': 19.0760,
    'user_lon': 72.8777,
    'radius_km': 10.0
}

response = requests.post(
    '${baseUrl}/api/evacuation/trigger',
    json=data
)
print(response.json())`
      }
    },
    {
      id: 'disaster-trigger',
      category: 'USER',
      method: 'POST',
      path: '/disaster/trigger',
      title: 'Report Disaster Zone',
      description: 'Report and activate a disaster zone. This creates a threat circle on the map and stores the event in the blockchain.',
      request: {
        type: 'earthquake',
        latitude: 19.0760,
        longitude: 72.8777,
        radius_meters: 5000,
        severity: 7
      },
      response: {
        disaster: {
          id: 'dis_123abc',
          type: 'earthquake',
          latitude: 19.0760,
          longitude: 72.8777,
          radius_meters: 5000,
          severity: 7,
          created_at: '2025-01-01T10:30:00Z',
          active: true,
          message: 'Disaster trigger successful! Danger zone activated.'
        }
      },
      codes: [200, 400],
      codeExamples: {
        curl: `curl -X POST ${baseUrl}/disaster/trigger \\
  -H "Content-Type: application/json" \\
  -d '{
    "type": "earthquake",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "radius_meters": 5000,
    "severity": 7
  }'`,
        javascript: `fetch('${baseUrl}/disaster/trigger', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    type: 'earthquake',
    latitude: 19.0760,
    longitude: 72.8777,
    radius_meters: 5000,
    severity: 7
  })
})
.then(res => res.json())
.then(data => console.log(data));`,
        python: `import requests

data = {
    'type': 'earthquake',
    'latitude': 19.0760,
    'longitude': 72.8777,
    'radius_meters': 5000,
    'severity': 7
}

response = requests.post(
    '${baseUrl}/disaster/trigger',
    json=data
)
print(response.json())`
      }
    },
    {
      id: 'disaster-active',
      category: 'USER',
      method: 'GET',
      path: '/disaster/active',
      title: 'Get Active Disasters',
      description: 'Retrieve all currently active disasters for real-time map visualization and threat zone display.',
      request: null,
      response: {
        active_disasters: [
          {
            id: 'dis_123abc',
            type: 'earthquake',
            latitude: 19.0760,
            longitude: 72.8777,
            radius_meters: 5000,
            severity: 7,
            created_at: '2025-01-01T10:30:00Z',
            active: true
          }
        ],
        count: 1,
        message: 'Live sync active - user map will show threat zones in real-time'
      },
      codes: [200],
      codeExamples: {
        curl: `curl -X GET ${baseUrl}/disaster/active`,
        javascript: `fetch('${baseUrl}/disaster/active')
  .then(res => res.json())
  .then(data => console.log(data));`,
        python: `import requests

response = requests.get('${baseUrl}/disaster/active')
print(response.json())`
      }
    },
    {
      id: 'disaster-clear',
      category: 'USER',
      method: 'DELETE',
      path: '/disaster/clear',
      title: 'Clear Active Disasters',
      description: 'Clear all active disasters from the system. Recommended for testing and development only.',
      request: null,
      response: {
        message: 'All active disasters cleared',
        count: 0
      },
      codes: [200],
      codeExamples: {
        curl: `curl -X DELETE ${baseUrl}/disaster/clear`,
        javascript: `fetch('${baseUrl}/disaster/clear', {
  method: 'DELETE'
})
.then(res => res.json())
.then(data => console.log(data));`,
        python: `import requests

response = requests.delete('${baseUrl}/disaster/clear')
print(response.json())`
      }
    },
    {
      id: 'news-disasters',
      category: 'USER',
      method: 'GET',
      path: '/news/disasters',
      title: 'Get Disaster News',
      description: 'Fetch curated news and information about current natural disasters worldwide.',
      request: null,
      response: {
        disasters: [
          {
            title: 'Earthquake in California',
            description: 'Magnitude 6.5 earthquake strikes...',
            timestamp: '2025-01-01T08:00:00Z'
          }
        ]
      },
      codes: [200],
      codeExamples: {
        curl: `curl -X GET ${baseUrl}/news/disasters`,
        javascript: `fetch('${baseUrl}/news/disasters')
  .then(res => res.json())
  .then(data => console.log(data));`,
        python: `import requests

response = requests.get('${baseUrl}/news/disasters')
print(response.json())`
      }
    },
    {
      id: 'health',
      category: 'ADMIN',
      method: 'GET',
      path: '/health',
      title: 'Health Check',
      description: 'Check API health status and service configuration.',
      request: null,
      response: {
        status: 'healthy',
        twilio_configured: true,
        overpass_osrm_reachable: true,
        timestamp: '2025-01-01T10:30:00Z'
      },
      codes: [200],
      codeExamples: {
        curl: `curl -X GET ${baseUrl}/health`,
        javascript: `fetch('${baseUrl}/health')
  .then(res => res.json())
  .then(data => console.log(data));`,
        python: `import requests

response = requests.get('${baseUrl}/health')
print(response.json())`
      }
    }
  ];

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'POST': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'DELETE': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getStatusColor = (code: number) => {
    if (code >= 200 && code < 300) return 'text-emerald-400';
    if (code >= 400 && code < 500) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white p-8">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto mb-12">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            DISHA API Documentation
          </h1>
          <p className="text-xl text-slate-400 mb-6">
            Integrate disaster management & emergency response into your applications
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <span className="px-4 py-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400 text-sm">
              REST API
            </span>
            <span className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm">
              Real-time Alerts
            </span>
            <span className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded-lg text-purple-400 text-sm">
              Evacuation Routes
            </span>
            <span className="px-4 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg text-orange-400 text-sm">
              Live Tracking
            </span>
          </div>
        </div>

        {/* Base URL */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6 mb-8">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Globe className="w-5 h-5 text-blue-400" />
              Base URL
            </h3>
            <button
              onClick={() => copyToClipboard(baseUrl, 'base-url')}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              {copiedCode === 'base-url' ? (
                <Check className="w-4 h-4 text-emerald-400" />
              ) : (
                <Copy className="w-4 h-4 text-slate-400" />
              )}
            </button>
          </div>
          <code className="text-blue-400 text-lg">{baseUrl}</code>
          <p className="text-slate-400 text-sm mt-2">
            No API key required for public endpoints
          </p>
        </div>

        {/* Quick Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <Zap className="w-8 h-8 text-yellow-400 mb-3" />
            <h3 className="text-lg font-semibold mb-2">Real-time Alerts</h3>
            <p className="text-slate-400 text-sm">
              Send SMS and voice alerts instantly to thousands of contacts
            </p>
          </div>
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <Shield className="w-8 h-8 text-emerald-400 mb-3" />
            <h3 className="text-lg font-semibold mb-2">Safe Routes</h3>
            <p className="text-slate-400 text-sm">
              Calculate evacuation paths to hospitals, shelters, and safe zones
            </p>
          </div>
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <Code className="w-8 h-8 text-blue-400 mb-3" />
            <h3 className="text-lg font-semibold mb-2">Easy Integration</h3>
            <p className="text-slate-400 text-sm">
              Simple REST API with examples in multiple languages
            </p>
          </div>
        </div>

        {/* Endpoints */}
        <div className="space-y-6">
          <h2 className="text-3xl font-bold mb-6">API Endpoints</h2>
          
          {endpoints.map((endpoint) => (
            <div
              key={endpoint.id}
              className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setExpandedEndpoint(expandedEndpoint === endpoint.id ? null : endpoint.id)}
                className="w-full p-6 flex items-center justify-between hover:bg-slate-800/80 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className={`px-3 py-1 rounded-lg border font-mono text-sm font-semibold ${getMethodColor(endpoint.method)}`}>
                    {endpoint.method}
                  </span>
                  <div className="text-left">
                    <code className="text-lg text-slate-200">{endpoint.path}</code>
                    <p className="text-sm text-slate-400 mt-1">{endpoint.title}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-slate-700/50 rounded-lg text-xs text-slate-400">
                    {endpoint.category}
                  </span>
                  {expandedEndpoint === endpoint.id ? (
                    <ChevronDown className="w-5 h-5 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  )}
                </div>
              </button>

              {expandedEndpoint === endpoint.id && (
                <div className="border-t border-slate-700 p-6 space-y-6">
                  <p className="text-slate-300">{endpoint.description}</p>

                  {/* Request Body */}
                  {endpoint.request && (
                    <div>
                      <h4 className="text-sm font-semibold text-slate-400 mb-2">REQUEST BODY</h4>
                      <div className="bg-slate-900/50 rounded-lg p-4 relative">
                        <button
                          onClick={() => copyToClipboard(JSON.stringify(endpoint.request, null, 2), `req-${endpoint.id}`)}
                          className="absolute top-2 right-2 p-2 hover:bg-slate-700 rounded-lg transition-colors"
                        >
                          {copiedCode === `req-${endpoint.id}` ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Copy className="w-4 h-4 text-slate-400" />
                          )}
                        </button>
                        <pre className="text-sm text-slate-300 overflow-x-auto">
                          <code>{JSON.stringify(endpoint.request, null, 2)}</code>
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Response */}
                  <div>
                    <h4 className="text-sm font-semibold text-slate-400 mb-2">RESPONSE</h4>
                    <div className="bg-slate-900/50 rounded-lg p-4 relative">
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(endpoint.response, null, 2), `res-${endpoint.id}`)}
                        className="absolute top-2 right-2 p-2 hover:bg-slate-700 rounded-lg transition-colors"
                      >
                        {copiedCode === `res-${endpoint.id}` ? (
                          <Check className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                      <pre className="text-sm text-slate-300 overflow-x-auto">
                        <code>{JSON.stringify(endpoint.response, null, 2)}</code>
                      </pre>
                    </div>
                  </div>

                  {/* Status Codes */}
                  <div>
                    <h4 className="text-sm font-semibold text-slate-400 mb-2">STATUS CODES</h4>
                    <div className="flex gap-2 flex-wrap">
                      {endpoint.codes.map((code) => (
                        <span key={code} className={`px-3 py-1 bg-slate-900/50 rounded-lg text-sm font-mono ${getStatusColor(code)}`}>
                          {code}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Code Examples */}
                  <div>
                    <h4 className="text-sm font-semibold text-slate-400 mb-2">CODE EXAMPLES</h4>
                    <div className="flex gap-2 mb-3">
                      {['curl', 'javascript', 'python'].map((lang) => (
                        <button
                          key={lang}
                          onClick={() => setSelectedLanguage(lang)}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            selectedLanguage === lang
                              ? 'bg-blue-500 text-white'
                              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                          }`}
                        >
                          {lang === 'curl' ? 'cURL' : lang.charAt(0).toUpperCase() + lang.slice(1)}
                        </button>
                      ))}
                    </div>
                    <div className="bg-slate-900/50 rounded-lg p-4 relative">
                      <button
                        onClick={() => copyToClipboard(endpoint.codeExamples[selectedLanguage], `code-${endpoint.id}-${selectedLanguage}`)}
                        className="absolute top-2 right-2 p-2 hover:bg-slate-700 rounded-lg transition-colors z-10"
                      >
                        {copiedCode === `code-${endpoint.id}-${selectedLanguage}` ? (
                          <Check className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                      <pre className="text-sm text-slate-300 overflow-x-auto">
                        <code>{endpoint.codeExamples[selectedLanguage]}</code>
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Best Practices */}
        <div className="mt-12 bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <h3 className="text-2xl font-bold mb-4">Best Practices</h3>
          <ul className="space-y-3 text-slate-300">
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 mt-1">✓</span>
              <span>Poll <code className="text-blue-400">/disaster/active</code> every 30-60 seconds for real-time map updates</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 mt-1">✓</span>
              <span>Always handle async processing for alert endpoints - they may take several seconds</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 mt-1">✓</span>
              <span>Implement proper error handling for all status codes (400, 500, etc.)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 mt-1">✓</span>
              <span>Use <code className="text-blue-400">/disaster/clear</code> only in development/testing environments</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default APIDocumentation;