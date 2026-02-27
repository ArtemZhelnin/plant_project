import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Upload, Clock, TrendingUp, Image as ImageIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import UploadZone from '../components/upload/UploadZone';
import { useAnalysisStore } from '../store/analysisStore';

const Dashboard: React.FC = () => {
  const [recentAnalyses, setRecentAnalyses] = useState([
    {
      id: 1,
      date: '2024-02-27',
      image: '/api/placeholder/100/100',
      rootLength: 45.2,
      leafArea: 342.1,
      confidence: 0.94
    },
    {
      id: 2,
      date: '2024-02-26',
      image: '/api/placeholder/100/100',
      rootLength: 38.7,
      leafArea: 298.5,
      confidence: 0.91
    }
  ]);

  const { startAnalysis } = useAnalysisStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0F1117] via-[#141821] to-[#0F1117] p-6">
      <div className="container">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
          <p className="text-gray-400">Upload and analyze plant images</p>
        </motion.div>

        <div className="grid-12">
          {/* Upload Section */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="col-span-12 lg:col-span-7"
          >
            <div className="glass-card p-8">
              <h2 className="text-2xl font-semibold mb-6 flex items-center gap-3">
                <Upload size={24} className="text-green-400" />
                Upload Image
              </h2>
              <UploadZone onUpload={startAnalysis} />
            </div>
          </motion.div>

          {/* Recent Analyses */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="col-span-12 lg:col-span-5"
          >
            <div className="glass-card p-8">
              <h2 className="text-2xl font-semibold mb-6 flex items-center gap-3">
                <Clock size={24} className="text-blue-400" />
                Recent Analyses
              </h2>
              
              <div className="space-y-4">
                {recentAnalyses.map((analysis, index) => (
                  <motion.div
                    key={analysis.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + index * 0.1 }}
                    className="glass-card p-4 cursor-pointer hover:neon-glow transition-all duration-300"
                  >
                    <Link to={`/analysis/${analysis.id}`}>
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
                          <img
                            src={analysis.image}
                            alt="Plant"
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-sm text-gray-400">{analysis.date}</span>
                            <span className="text-xs px-2 py-1 bg-green-400/20 text-green-400 rounded">
                              {Math.round(analysis.confidence * 100)}%
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-gray-400">Root:</span>
                              <span className="ml-2 text-white">{analysis.rootLength}mm</span>
                            </div>
                            <div>
                              <span className="text-gray-400">Leaf:</span>
                              <span className="ml-2 text-white">{analysis.leafArea}mm²</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </div>

              {recentAnalyses.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <ImageIcon size={48} className="mx-auto mb-4 opacity-50" />
                  <p>No analyses yet</p>
                  <p className="text-sm">Upload your first plant image to get started</p>
                </div>
              )}
            </div>
          </motion.div>

          {/* Stats Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="col-span-12 md:col-span-4"
          >
            <div className="glass-card p-6 text-center">
              <TrendingUp size={32} className="mx-auto mb-4 text-green-400" />
              <h3 className="text-2xl font-bold mb-2">{recentAnalyses.length}</h3>
              <p className="text-gray-400">Total Analyses</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="col-span-12 md:col-span-4"
          >
            <div className="glass-card p-6 text-center">
              <Clock size={32} className="mx-auto mb-4 text-blue-400" />
              <h3 className="text-2xl font-bold mb-2">
                {recentAnalyses.length > 0 ? 'Today' : 'N/A'}
              </h3>
              <p className="text-gray-400">Last Analysis</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="col-span-12 md:col-span-4"
          >
            <div className="glass-card p-6 text-center">
              <TrendingUp size={32} className="mx-auto mb-4 text-purple-400" />
              <h3 className="text-2xl font-bold mb-2">
                {recentAnalyses.length > 0 
                  ? Math.round(recentAnalyses.reduce((acc, a) => acc + a.confidence, 0) / recentAnalyses.length * 100)
                  : 0}%
              </h3>
              <p className="text-gray-400">Avg Confidence</p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
