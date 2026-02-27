import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Download, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import UploadZone from '../components/upload/UploadZone';
import ImageViewer from '../components/viewer/ImageViewer';
import MetricsPanel from '../components/metrics/MetricsPanel';
import { useAnalysisStore } from '../store/analysisStore';

interface AnalysisData {
  metrics: {
    root_length_mm: number;
    stem_length_mm: number;
    leaf_area_mm2: number;
    root_area_mm2: number;
  };
  overlay: string;
  confidence: number;
}

const Analysis: React.FC = () => {
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const { currentAnalysis, setCurrentAnalysis } = useAnalysisStore();

  const handleUpload = async (file: File) => {
    setIsAnalyzing(true);
    setOriginalImage(URL.createObjectURL(file));

    // Simulate API call
    setTimeout(() => {
      const mockData: AnalysisData = {
        metrics: {
          root_length_mm: 45.2,
          stem_length_mm: 28.7,
          leaf_area_mm2: 342.1,
          root_area_mm2: 125.4
        },
        overlay: URL.createObjectURL(file), // Mock overlay
        confidence: 0.94
      };
      
      setAnalysisData(mockData);
      setCurrentAnalysis(mockData);
      setIsAnalyzing(false);
    }, 3000);
  };

  const handleDownload = () => {
    if (!analysisData) return;
    
    const dataStr = JSON.stringify(analysisData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `plant-analysis-${Date.now()}.json`;
    
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
          className="mb-8 flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <button className="btn-secondary p-2">
                <ArrowLeft size={20} />
              </button>
            </Link>
            <div>
              <h1 className="text-4xl font-bold">Plant Analysis</h1>
              <p className="text-gray-400">Upload and analyze plant morphology</p>
            </div>
          </div>
          
          {analysisData && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={handleDownload}
              className="btn-primary flex items-center gap-2"
            >
              <Download size={20} />
              Download Results
            </motion.button>
          )}
        </motion.div>

        {!originalImage ? (
          /* Upload Section */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="glass-card p-12">
              <UploadZone onUpload={handleUpload} />
            </div>
          </motion.div>
        ) : (
          /* Analysis Results */
          <div className="grid-12">
            {/* Image Viewer */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="col-span-12 lg:col-span-8"
            >
              <div className="glass-card p-6">
                <ImageViewer
                  originalImage={originalImage}
                  overlayImage={analysisData?.overlay}
                  isAnalyzing={isAnalyzing}
                />
              </div>
            </motion.div>

            {/* Metrics Panel */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="col-span-12 lg:col-span-4"
            >
              <MetricsPanel
                metrics={analysisData?.metrics}
                confidence={analysisData?.confidence}
                isAnalyzing={isAnalyzing}
              />
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="col-span-12"
            >
              <div className="glass-card p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button className="btn-secondary flex items-center gap-2">
                      <RotateCw size={20} />
                      Analyze Another
                    </button>
                    <button className="btn-secondary flex items-center gap-2">
                      <ZoomIn size={20} />
                      Zoom
                    </button>
                    <button className="btn-secondary flex items-center gap-2">
                      <ZoomOut size={20} />
                      Reset
                    </button>
                  </div>
                  
                  {analysisData && (
                    <div className="text-right">
                      <div className="text-sm text-gray-400 mb-1">Analysis Confidence</div>
                      <div className="text-2xl font-bold text-green-400">
                        {Math.round(analysisData.confidence * 100)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Analysis;
