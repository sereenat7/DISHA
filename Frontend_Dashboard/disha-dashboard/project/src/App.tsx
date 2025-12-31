import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import TriggerForm from './components/TriggerForm';
import MapContainer from './components/MapContainer';
import NewsList from './components/NewsList';
import APIDocumentation from './components/APIDocumentation';
import { ViewType, Disaster } from './types';

function App() {
  const [activeView, setActiveView] = useState<ViewType>('home');
  const [disasters, setDisasters] = useState<Disaster[]>([]);

  const handleDisasterTriggered = (disaster: Disaster) => {
    setDisasters((prev) => [...prev, disaster]);
  };

  const renderContent = () => {
    switch (activeView) {
      case 'home':
        return <Dashboard disasters={disasters} />;
      case 'trigger':
        return (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 h-full">
            <div className="space-y-6">
              <TriggerForm onDisasterTriggered={handleDisasterTriggered} />
            </div>
            <div className="h-[600px] xl:h-full">
              <MapContainer disasters={disasters} />
            </div>
          </div>
        );
      case 'news':
        return <NewsList />;
      case 'developers':
        return <APIDocumentation />;
      default:
        return <Dashboard disasters={disasters} />;
    }
  };

  const getHeaderTitle = () => {
    switch (activeView) {
      case 'home':
        return 'Dashboard Overview';
      case 'trigger':
        return 'Trigger Disaster';
      case 'news':
        return 'Disaster News Feed';
      case 'developers':
        return 'API Documentation';
      default:
        return 'Dashboard';
    }
  };

  const getHeaderSubtitle = () => {
    switch (activeView) {
      case 'home':
        return 'Real-time monitoring and analytics';
      case 'trigger':
        return 'Create and manage disaster events';
      case 'news':
        return 'Latest updates and reports';
      case 'developers':
        return 'Integrate DISHA into your applications';
      default:
        return '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <Sidebar activeView={activeView} onViewChange={setActiveView} />

      <div className="ml-64 min-h-screen">
        <Header title={getHeaderTitle()} subtitle={getHeaderSubtitle()} />

        <main className="p-8">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;