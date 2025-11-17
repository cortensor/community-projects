import { useState } from 'react';
import Sidebar from './components/Sidebar';
import OverviewTab from './views/OverviewTab';
import NetworkTab from './views/NetworkTab';
import NodesTab from './views/NodesTab';
import SessionsTab from './views/SessionsTab';
import TasksTab from './views/TasksTab';
import ConfigTab from './views/ConfigTab';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab />;
      case 'network':
        return <NetworkTab />;
      case 'nodes':
        return <NodesTab />;
      case 'sessions':
        return <SessionsTab />;
      case 'tasks':
        return <TasksTab />;
      case 'config':
        return <ConfigTab />;
      default:
        return <OverviewTab />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        activeTab={activeTab} 
        onTabChange={setActiveTab}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;
