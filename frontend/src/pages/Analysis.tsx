import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import UploadZone from '../components/upload/UploadZone.tsx';
import ImageViewer from '../components/viewer/ImageViewer.tsx';
import MetricsPanel from '../components/metrics/MetricsPanel.tsx';
import { useAnalysisStore } from '../store/analysisStore.ts';

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
  const { setCurrentAnalysis } = useAnalysisStore();

  const handleAnalyzeAnother = () => {
    setAnalysisData(null);
    setOriginalImage(null);
    setIsAnalyzing(false);
    setCurrentAnalysis(null);
  };

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
    <div className="min-h-screen bg-[#0F1117] p-6">
      <div className="container">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 flex items-center justify-between"
        >
          <div>
            <h1 className="text-3xl md:text-4xl font-semibold">Анализ растения</h1>
            <p className="text-gray-400">Загрузите изображение, получите сегментацию и измерения</p>
          </div>
          
          {analysisData && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={handleDownload}
              className="btn-primary flex items-center gap-2"
            >
              <Download size={20} />
              Скачать результат
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
          <div className="space-y-4">
            {/* Image Viewer */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="glass-card p-4">
                <ImageViewer
                  originalImage={originalImage}
                  overlayImage={analysisData?.overlay}
                  isAnalyzing={isAnalyzing}
                />
              </div>
            </motion.div>

            {/* Compact Toolbar */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <div className="analysis-toolbar">
                <div className="analysis-toolbar__group">
                  <button onClick={handleAnalyzeAnother} className="analysis-toolbar__btn">
                    <RotateCw size={16} />
                    Новый анализ
                  </button>
                </div>
                <div className="analysis-toolbar__group">
                  <button onClick={() => window.dispatchEvent(new CustomEvent('viewer:zoomOut'))} className="analysis-toolbar__icon" aria-label="Отдалить">
                    <ZoomOut size={16} />
                  </button>
                  <button onClick={() => window.dispatchEvent(new CustomEvent('viewer:zoomIn'))} className="analysis-toolbar__icon" aria-label="Приблизить">
                    <ZoomIn size={16} />
                  </button>
                  <button onClick={() => window.dispatchEvent(new CustomEvent('viewer:reset'))} className="analysis-toolbar__icon" aria-label="Сброс">
                    <RotateCw size={16} />
                  </button>
                </div>
              </div>
            </motion.div>

            {/* Metrics (under image) */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <MetricsPanel
                metrics={analysisData?.metrics}
                confidence={analysisData?.confidence}
                isAnalyzing={isAnalyzing}
              />
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Analysis;
