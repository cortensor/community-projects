import React, { useState, useEffect, useCallback, useMemo } from 'react';
// --- Icons ---
import { RefreshCw, Zap, Search, X, BarChart, Hash, Server } from 'lucide-react';

// --- Configuration ---
// --- UPDATED: We now call the Cortensor API directly! ---
const CORTENSOR_LEADERBOARD_URL = "https://db-be-7.cortensor.network/leaderboard";


// --- HELPER COMPONENTS (MOVED OUTSIDE) ---

// --- Helper Component - Header ---
const Header = ({ onRefresh, isLoading }) => (
  <header className="w-full max-w-5xl mx-auto px-4 pt-8 pb-4">
    <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
      <div className="flex items-center gap-3">
        <div className="p-3 bg-blue-600 rounded-lg">
          <Zap className="text-white h-6 w-6" />
        </div>
        <h1 className="text-3xl font-bold text-white tracking-tight">
          CortensorPulse
        </h1>
      </div>
      <button
        onClick={onRefresh}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white rounded-lg font-medium shadow-md hover:bg-gray-600 transition-all disabled:opacity-50 disabled:cursor-wait"
      >
        <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        {isLoading ? 'Loading...' : 'Refresh'}
      </button>
    </div>
    <p className="text-gray-300 mt-2 text-center sm:text-left">
      A real-time dashboard of the Cortensor Network's Node Leaderboard.
    </p>
  </header>
);

// --- Helper Component - StatCard (for SummaryCards) ---
const StatCard = ({ icon, title, value }) => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 flex items-center gap-4 shadow-lg">
    <div className="flex-shrink-0 p-3 bg-blue-600/20 text-blue-400 rounded-full">
      {React.cloneElement(icon, { className: 'h-6 w-6' })}
    </div>
    <div>
      <div className="text-sm font-medium text-gray-400 uppercase tracking-wider">{title}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  </div>
);

// --- Helper Component - SummaryCards ---
const SummaryCards = ({ leaderboard }) => {
  const stats = useMemo(() => {
    const totalNodes = leaderboard.length;
    if (totalNodes === 0) {
      return { totalNodes: 0, avgScore: 0, avgLevel: 0 };
    }
    
    const totalScore = leaderboard.reduce((acc, node) => acc + (node.total_score || 0), 0);
    const totalLevel = leaderboard.reduce((acc, node) => acc + (node.level || 0), 0);
    
    return {
      totalNodes: totalNodes,
      avgScore: (totalScore / totalNodes).toFixed(2),
      avgLevel: (totalLevel / totalNodes).toFixed(2),
    };
  }, [leaderboard]);

  return (
    <div className="w-full max-w-5xl mx-auto p-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={<Server />} title="Total Active Nodes" value={stats.totalNodes} />
        <StatCard icon={<BarChart />} title="Average Total Score" value={stats.avgScore} />
        <StatCard icon={<Hash />} title="Average Level (Quant.)" value={stats.avgLevel} />
      </div>
    </div>
  );
};

// --- Helper Component - LeaderboardTable ---
const LeaderboardTable = ({ 
  leaderboard, 
  sortBy, 
  setSortBy, 
  searchQuery, 
  setSearchQuery, 
  onNodeClick 
}) => {
  
  // Sorting & Filtering Logic
  const filteredAndSortedLeaderboard = useMemo(() => {
    const filteredData = leaderboard.filter(node => 
      node.address && node.address.toLowerCase().includes(searchQuery.toLowerCase())
    );
    
    const data = [...filteredData]; 
    if (sortBy === 'rank') {
      data.sort((a, b) => a.rank - b.rank);
    } else if (sortBy === 'score') {
      data.sort((a, b) => (b.total_score || 0) - (a.total_score || 0));
    }
    return data;
  }, [leaderboard, sortBy, searchQuery]); 
  
  return (
    <div className="w-full max-w-5xl mx-auto p-4">
      
      {/* Search Bar & Sort Buttons */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-4">
        <div className="relative flex-grow">
          <input
            type="text"
            placeholder="Search by Node Address (e.g., 0x...)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-700 text-white p-3 pl-10 rounded-lg border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
        </div>
        
        <div className="flex justify-end gap-2 flex-shrink-0">
          <button
            onClick={() => setSortBy('rank')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              sortBy === 'rank' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Sort by Rank
          </button>
          <button
            onClick={() => setSortBy('score')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              sortBy === 'score' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Sort by Score (High to Low)
          </button>
        </div>
      </div>
      
      {/* Leaderboard Table */}
      <div className="shadow-2xl rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-300 uppercase tracking-wider">
                Rank
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-300 uppercase tracking-wider">
                Node Address
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-300 uppercase tracking-wider">
                Level (Quant. Points)
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-300 uppercase tracking-wider">
                Total Score (Qual.)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {filteredAndSortedLeaderboard.map((node, index) => (
              <tr 
                key={node.address} 
                className="hover:bg-gray-700/50 transition-colors cursor-pointer"
                onClick={() => onNodeClick(node)} 
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`text-lg font-bold ${
                    index + 1 === 1 ? 'text-yellow-400' :
                    index + 1 === 2 ? 'text-gray-300' :
                    index + 1 === 3 ? 'text-yellow-600' : 'text-gray-400'
                  }`}>
                    {index + 1}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-base font-medium text-white" title={node.address}>
                    {node.address ? `${node.address.substring(0, 6)}...${node.address.substring(node.address.length - 4)}` : 'N/A'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-lg font-semibold text-blue-400">
                    {typeof node.level === 'number' ? node.level : 'N/A'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-lg font-semibold text-green-400">
                    {typeof node.total_score === 'number' ? node.total_score.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-center text-gray-400 text-sm mt-4">
        Last updated: {new Date().toLocaleTimeString()}
      </p>
    </div>
  );
};

// --- Helper Component - StatusDisplay ---
const StatusDisplay = ({ isLoading, error, leaderboard }) => {
  if (isLoading && leaderboard.length === 0) {
    return (
      <div className="text-center p-10 text-gray-300">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
        <p className="text-lg font-medium">Loading Real-Time Leaderboard...</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="w-full max-w-5xl mx-auto p-4">
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-6 py-4 rounded-lg">
          <h3 className="font-bold text-lg">Connection Error</h3>
          <p>{error}</p>
          {/* --- UPDATED: Removed backend message --- */}
          <p className="mt-2 text-sm">Please try refreshing the page. The Cortensor API might be temporarily unavailable.</p>
        </div>
      </div>
    );
  }
  if (!isLoading && leaderboard.length === 0) {
     return (
      <div className="w-full max-w-5xl mx-auto p-4">
        <div className="text-center p-10 text-gray-400 bg-gray-800 border border-gray-700 rounded-lg">
          <p className="text-lg font-medium">No node data found.</p>
          <p className="text-sm mt-2">Could not fetch data or the leaderboard is empty.</p>
        </div>
      </div>
    );
  }
 return null;
};
  
  
// --- Helper Component - NodeDetailModal ---
const NodeDetailModal = ({ node, onClose }) => {
  // Helper to format UNIX timestamp
  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleString();
  }
  
  // Helper to render a stat row
  const DetailRow = ({ label, value }) => (
    <div className="flex justify-between items-center py-3 border-b border-gray-700">
      <span className="text-sm font-medium text-gray-400">{label}</span>
      <span className="text-base font-medium text-white break-all text-right">{String(value)}</span>
    </div>
  );
  
  return (
    // Backdrop
    <div 
      className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      {/* Modal Content */}
      <div 
        className="w-full max-w-2xl bg-gray-800 border border-gray-700 rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal
      >
        {/* Header */}
        <div className="flex justify-between items-center p-5 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Node Details</h2>
          <button 
            onClick={onClose}
            className="p-1 rounded-full text-gray-400 hover:bg-gray-700 hover:text-white transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        
        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <h3 className="text-lg font-semibold text-blue-400 mb-2">Identifier</h3>
          <DetailRow label="Node Address (Miner)" value={node.address} />
          <DetailRow label="Node ID" value={node.node_id} />
          
          <h3 className="text-lg font-semibold text-blue-400 mt-6 mb-2">Performance Scores</h3>
          <DetailRow label="Total Score (Qualitative)" value={node.total_score} />
          <DetailRow label="Total Points (Quantitative)" value={node.level} />
          <DetailRow label="Ping Counter" value={node.ping_counter} />
          <DetailRow label="Last Active" value={formatDate(node.last_active)} />
          
          <h3 className="text-lg font-semibold text-blue-400 mt-6 mb-2">Cognitive Points</h3>
          <DetailRow label="Create Point" value={node.createPoint} />
          <DetailRow label="Prepare Point" value={node.preparePoint} />
          <DetailRow label="Precommit Point" value={node.precommitPoint} />
          <DetailRow label="Commit Point" value={node.commitPoint} />
          
          <h3 className="text-lg font-semibold text-blue-400 mt-6 mb-2">Quantitative Stats</h3>
          <DetailRow label="Total Validations" value={node.quantitive?.totalCount} />
          <DetailRow label="Normal Count" value={node.quantitive?.normalCount} />
          <DetailRow label="Abnormal Count" value={node.quantitive?.abnormalCount} />
          <DetailRow label="Last Validated" value={formatDate(node.quantitive?.lastValidated)} />
        </div>
      </div>
    </div>
  );
};


/**
 * Main Application Component
 * This now just holds state and passes props to the helper components.
 */
export default function App() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for new features
  const [sortBy, setSortBy] = useState('rank'); 
  const [searchQuery, setSearchQuery] = useState(''); 
  const [selectedNode, setSelectedNode] = useState(null); 

  // --- UPDATED: Data Fetching ---
  const fetchLeaderboard = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      // --- UPDATED: Fetch directly from Cortensor API ---
      const response = await fetch(CORTENSOR_LEADERBOARD_URL);
      if (!response.ok) throw new Error(`Cortensor API error! Status: ${response.status}`);
      
      const data = await response.json();
      
      // --- NEW: Data formatting moved from backend to frontend ---
      let dataArray = [];
      if (Array.isArray(data)) {
        dataArray = data;
      } else {
        console.error('API returned an unexpected data format. Expected an array.');
      }
    
      const formattedLeaderboard = dataArray.map((node, index) => ({
        ...node, // Include all original node data
        rank: index + 1, 
        address: node.miner, // Use the correct 'miner' field
        total_score: node.qualitative.totalScore, // Use the correct 'totalScore' field
        level: node.quantitive.point // Use the correct 'point' field
      }));
      // --- END OF NEW LOGIC ---

      setLeaderboard(formattedLeaderboard); 

    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
      // --- UPDATED: New error message ---
      setError('Failed to fetch data from Cortensor API. Is the network down?');
    } finally {
      setIsLoading(false);
    }
  }, []); 

  // Initial Data Load
  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]); 

  
  // --- Main Render ---
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans">
      <Header onRefresh={() => fetchLeaderboard()} isLoading={isLoading} />
      
      <main>
        <StatusDisplay isLoading={isLoading} error={error} leaderboard={leaderboard} />
        
        {!error && !isLoading && (
          <>
            <SummaryCards leaderboard={leaderboard} />
            <LeaderboardTable 
              leaderboard={leaderboard}
              sortBy={sortBy}
              setSortBy={setSortBy}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              onNodeClick={setSelectedNode}
            />
          </>
        )}
      </main>
      
      {/* Render Modal if a node is selected */}
      {selectedNode && (
        <NodeDetailModal 
          node={selectedNode} 
          onClose={() => setSelectedNode(null)} 
        />
      )}
      
      <footer className="text-center p-8 text-gray-500 text-sm">
        Cortensor Hackathon #2 Submission
      </footer>
    </div>
  );
}

