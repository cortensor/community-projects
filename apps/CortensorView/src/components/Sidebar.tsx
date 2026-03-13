import { Home, Activity, Layers, Settings, Database, Users, ChevronLeft, ChevronRight } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

const navigation = [
  { id: 'overview', name: 'Overview', icon: Home },
  { id: 'network', name: 'Network', icon: Activity },
  { id: 'nodes', name: 'Nodes', icon: Database },
  { id: 'sessions', name: 'Sessions', icon: Layers },
  { id: 'tasks', name: 'Tasks', icon: Users },
  { id: 'config', name: 'Config', icon: Settings },
];

export default function Sidebar({ activeTab, onTabChange, isOpen, onToggle }: SidebarProps) {
  return (
    <div 
      className={`bg-white border-r border-gray-200 h-screen flex flex-col transition-all duration-300 ease-in-out relative ${
        isOpen ? 'w-64' : 'w-20'
      }`}
    >
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-8 z-10 p-1.5 bg-white rounded-full border border-gray-200 shadow-md hover:shadow-lg hover:bg-gray-50 transition-all duration-200"
      >
        {isOpen ? (
          <ChevronLeft className="w-4 h-4 text-gray-700" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-700" />
        )}
      </button>

      {/* Header */}
      <div className={`p-4 border-b border-gray-200 transition-all duration-300 ${isOpen ? '' : 'px-3'}`}>
        <div className={`flex items-center ${isOpen ? 'space-x-3' : 'justify-center'}`}>
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
            <Activity className="w-5 h-5 text-white" />
          </div>
          {isOpen && (
            <div className="overflow-hidden">
              <h1 className="text-lg font-semibold text-gray-900 whitespace-nowrap">Cortensor</h1>
              <p className="text-xs text-gray-500 whitespace-nowrap">Visual Dashboard</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className={`flex-1 py-3 ${isOpen ? 'px-3' : 'px-2'}`}>
        <div className="space-y-0.5">
          {navigation.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center ${isOpen ? 'space-x-3 px-3' : 'justify-center px-0'} py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
                title={!isOpen ? item.name : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {isOpen && <span className="whitespace-nowrap">{item.name}</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className={`p-3 border-t border-gray-200 ${isOpen ? '' : 'px-2'}`}>
        <div className={`flex items-center ${isOpen ? 'space-x-3 px-3' : 'justify-center px-0'} py-2`}>
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-medium text-gray-600">CT</span>
          </div>
          {isOpen && (
            <div className="flex-1 min-w-0 overflow-hidden">
              <p className="text-sm font-medium text-gray-900 truncate">Devnet 7</p>
              <p className="text-xs text-gray-500 truncate">Live Network</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
