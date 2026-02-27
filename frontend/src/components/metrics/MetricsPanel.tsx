import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Activity, Square, Ruler } from 'lucide-react';

interface Metrics {
  root_length_mm?: number;
  stem_length_mm?: number;
  leaf_area_mm2?: number;
  root_area_mm2?: number;
}

interface MetricsPanelProps {
  metrics?: Metrics;
  confidence?: number;
  isAnalyzing?: boolean;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({ 
  metrics, 
  confidence, 
  isAnalyzing = false 
}) => {
  const metricItems = [
    {
      label: 'Root Length',
      value: metrics?.root_length_mm,
      unit: 'mm',
      icon: <Ruler size={20} />,
      color: 'green'
    },
    {
      label: 'Stem Length',
      value: metrics?.stem_length_mm,
      unit: 'mm',
      icon: <Activity size={20} />,
      color: 'blue'
    },
    {
      label: 'Leaf Area',
      value: metrics?.leaf_area_mm2,
      unit: 'mm²',
      icon: <Square size={20} />,
      color: 'purple'
    },
    {
      label: 'Root Area',
      value: metrics?.root_area_mm2,
      unit: 'mm²',
      icon: <TrendingUp size={20} />,
      color: 'orange'
    }
  ];

  if (isAnalyzing) {
    return (
      <div className="glass-card p-6">
        <h2 className="text-2xl font-semibold mb-6">Analysis Results</h2>
        
        <div className="space-y-4">
          {metricItems.map((item, index) => (
            <div key={index} className="metric-card">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <div className="text-gray-400">{item.icon}</div>
                  <span className="text-gray-400">{item.label}</span>
                </div>
              </div>
              <div className="skeleton h-8 w-24 rounded" />
            </div>
          ))}
        </div>
        
        <div className="mt-6 p-4 bg-gray-800 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Confidence</span>
            <div className="skeleton h-4 w-16 rounded" />
          </div>
          <div className="skeleton h-2 w-full rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h2 className="text-2xl font-semibold mb-6">Analysis Results</h2>
      
      <div className="space-y-4">
        {metricItems.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="metric-card"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className={`${
                  item.color === 'green' ? 'text-green-400' :
                  item.color === 'blue' ? 'text-blue-400' :
                  item.color === 'purple' ? 'text-purple-400' :
                  'text-orange-400'
                }`}>
                  {item.icon}
                </div>
                <span className="text-gray-400">{item.label}</span>
              </div>
            </div>
            <div className="text-2xl font-bold">
              {item.value ? `${item.value.toFixed(1)} ${item.unit}` : '-'}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Confidence Score */}
      {confidence !== undefined && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-6 p-4 bg-gray-800 rounded-lg"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Confidence Score</span>
            <span className="text-lg font-semibold text-green-400">
              {Math.round(confidence * 100)}%
            </span>
          </div>
          <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${confidence * 100}%` }}
              transition={{ duration: 1, delay: 0.5 }}
              className={`h-full rounded-full ${
                confidence >= 0.9 ? 'bg-green-400' :
                confidence >= 0.7 ? 'bg-yellow-400' :
                'bg-red-400'
              }`}
            />
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {confidence >= 0.9 ? 'High confidence analysis' :
             confidence >= 0.7 ? 'Moderate confidence analysis' :
             'Low confidence - consider re-analysis'}
          </div>
        </motion.div>
      )}

      {/* Summary Stats */}
      {metrics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-6 p-4 bg-gray-800 rounded-lg"
        >
          <h3 className="text-sm font-semibold text-gray-400 mb-3">Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Total Length</span>
              <span className="text-white">
                {((metrics.root_length_mm || 0) + (metrics.stem_length_mm || 0)).toFixed(1)} mm
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Total Area</span>
              <span className="text-white">
                {((metrics.leaf_area_mm2 || 0) + (metrics.root_area_mm2 || 0)).toFixed(1)} mm²
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Root/Stem Ratio</span>
              <span className="text-white">
                {metrics.stem_length_mm && metrics.root_length_mm 
                  ? (metrics.root_length_mm / metrics.stem_length_mm).toFixed(2)
                  : '-'
                }
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default MetricsPanel;
