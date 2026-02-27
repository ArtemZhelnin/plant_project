import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Download, Calendar, Filter } from 'lucide-react';
import { Link } from 'react-router-dom';

interface HistoryItem {
  id: string;
  date: string;
  image: string;
  rootLength: number;
  stemLength: number;
  leafArea: number;
  rootArea: number;
  confidence: number;
  plantType: 'wheat' | 'arugula';
}

const History: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'wheat' | 'arugula'>('all');
  
  const [history] = useState<HistoryItem[]>([
    {
      id: '1',
      date: '2024-02-27 14:30',
      image: '/api/placeholder/80/80',
      rootLength: 45.2,
      stemLength: 28.7,
      leafArea: 342.1,
      rootArea: 125.4,
      confidence: 0.94,
      plantType: 'wheat'
    },
    {
      id: '2',
      date: '2024-02-27 13:15',
      image: '/api/placeholder/80/80',
      rootLength: 38.7,
      stemLength: 22.3,
      leafArea: 298.5,
      rootArea: 98.2,
      confidence: 0.91,
      plantType: 'arugula'
    },
    {
      id: '3',
      date: '2024-02-26 16:45',
      image: '/api/placeholder/80/80',
      rootLength: 52.1,
      stemLength: 31.4,
      leafArea: 412.7,
      rootArea: 156.8,
      confidence: 0.96,
      plantType: 'wheat'
    }
  ]);

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.date.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterType === 'all' || item.plantType === filterType;
    return matchesSearch && matchesFilter;
  });

  const handleDownload = (item: HistoryItem) => {
    const dataStr = JSON.stringify(item, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `plant-analysis-${item.id}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0F1117] via-[#141821] to-[#0F1117] p-6">
      <div className="container">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2">Analysis History</h1>
          <p className="text-gray-400">View and download previous plant analyses</p>
        </motion.div>

        {/* Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-6 mb-6"
        >
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex flex-col md:flex-row gap-4 flex-1">
              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search size={20} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by date..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-[#141821] border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors"
                />
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2">
                <Filter size={20} className="text-gray-400" />
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value as 'all' | 'wheat' | 'arugula')}
                  className="bg-[#141821] border border-gray-700 rounded-lg text-white px-4 py-2 focus:outline-none focus:border-green-400 transition-colors"
                >
                  <option value="all">All Plants</option>
                  <option value="wheat">Wheat</option>
                  <option value="arugula">Arugula</option>
                </select>
              </div>
            </div>

            <div className="text-gray-400">
              {filteredHistory.length} {filteredHistory.length === 1 ? 'result' : 'results'}
            </div>
          </div>
        </motion.div>

        {/* Results Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-6"
        >
          {filteredHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Date & Time</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Image</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Plant Type</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Root Length</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Leaf Area</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Confidence</th>
                    <th className="text-left py-4 px-4 text-gray-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((item, index) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + index * 0.05 }}
                      className="border-b border-gray-800 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <Calendar size={16} className="text-gray-400" />
                          <span>{item.date}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <Link to={`/analysis/${item.id}`}>
                          <div className="w-12 h-12 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-green-400 transition-all">
                            <img
                              src={item.image}
                              alt="Plant"
                              className="w-full h-full object-cover"
                            />
                          </div>
                        </Link>
                      </td>
                      <td className="py-4 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          item.plantType === 'wheat' 
                            ? 'bg-yellow-400/20 text-yellow-400' 
                            : 'bg-green-400/20 text-green-400'
                        }`}>
                          {item.plantType.charAt(0).toUpperCase() + item.plantType.slice(1)}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-white font-medium">{item.rootLength}mm</span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-white font-medium">{item.leafArea}mm²</span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-green-400 transition-all duration-300"
                              style={{ width: `${item.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-400">
                            {Math.round(item.confidence * 100)}%
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <button
                          onClick={() => handleDownload(item)}
                          className="btn-secondary p-2 hover:bg-green-400/10 hover:border-green-400 transition-all"
                          title="Download results"
                        >
                          <Download size={16} />
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Calendar size={48} className="mx-auto mb-4 text-gray-400 opacity-50" />
              <h3 className="text-xl font-semibold mb-2">No results found</h3>
              <p className="text-gray-400">
                {searchTerm || filterType !== 'all' 
                  ? 'Try adjusting your search or filters'
                  : 'No analyses have been performed yet'
                }
              </p>
              {!searchTerm && filterType === 'all' && (
                <Link to="/analysis" className="inline-block mt-4">
                  <button className="btn-primary">Start Your First Analysis</button>
                </Link>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default History;
