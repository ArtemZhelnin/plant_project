import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Maximize2, RotateCw } from 'lucide-react';

interface ImageViewerProps {
  originalImage: string;
  overlayImage?: string;
  isAnalyzing?: boolean;
}

const ImageViewer: React.FC<ImageViewerProps> = ({ 
  originalImage, 
  overlayImage, 
  isAnalyzing = false 
}) => {
  const [viewMode, setViewMode] = useState<'original' | 'overlay' | 'comparison'>('original');
  const [zoom, setZoom] = useState(1);
  const [sliderPosition, setSliderPosition] = useState(50);

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleReset = () => {
    setZoom(1);
    setSliderPosition(50);
  };

  return (
    <div className="space-y-4">
      {/* View Mode Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('original')}
            className={`px-4 py-2 rounded-lg transition-all ${
              viewMode === 'original' 
                ? 'bg-green-400 text-black' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Eye size={16} className="inline mr-2" />
            Original
          </button>
          
          <button
            onClick={() => setViewMode('overlay')}
            disabled={!overlayImage || isAnalyzing}
            className={`px-4 py-2 rounded-lg transition-all ${
              viewMode === 'overlay' 
                ? 'bg-green-400 text-black' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          >
            <EyeOff size={16} className="inline mr-2" />
            Segmentation
          </button>
          
          <button
            onClick={() => setViewMode('comparison')}
            disabled={!overlayImage || isAnalyzing}
            className={`px-4 py-2 rounded-lg transition-all ${
              viewMode === 'comparison' 
                ? 'bg-green-400 text-black' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          >
            <Maximize2 size={16} className="inline mr-2" />
            Compare
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
          >
            <span className="text-sm">−</span>
          </button>
          <span className="text-sm text-gray-400 min-w-[60px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
          >
            <span className="text-sm">+</span>
          </button>
          <button
            onClick={handleReset}
            className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
          >
            <RotateCw size={16} />
          </button>
        </div>
      </div>

      {/* Image Display */}
      <div className="relative bg-gray-900 rounded-lg overflow-hidden" style={{ height: '500px' }}>
        {isAnalyzing ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <div className="w-16 h-16 border-4 border-green-400 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-gray-400">Analyzing image...</p>
            </motion.div>
          </div>
        ) : (
          <div className="relative w-full h-full overflow-hidden">
            {viewMode === 'original' && (
              <motion.img
                key="original"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                src={originalImage}
                alt="Original plant image"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ transform: `scale(${zoom})` }}
              />
            )}

            {viewMode === 'overlay' && overlayImage && (
              <motion.img
                key="overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                src={overlayImage}
                alt="Segmentation overlay"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ transform: `scale(${zoom})` }}
              />
            )}

            {viewMode === 'comparison' && overlayImage && (
              <div className="relative w-full h-full">
                {/* Original Image */}
                <img
                  src={originalImage}
                  alt="Original plant image"
                  className="absolute inset-0 w-full h-full object-contain"
                  style={{ transform: `scale(${zoom})` }}
                />
                
                {/* Overlay Image with slider */}
                <div
                  className="absolute inset-0 overflow-hidden"
                  style={{ 
                    width: `${sliderPosition}%`,
                    transform: `scale(${zoom})`,
                    transformOrigin: 'left center'
                  }}
                >
                  <img
                    src={overlayImage}
                    alt="Segmentation overlay"
                    className="absolute inset-0 w-full h-full object-contain"
                  />
                </div>

                {/* Slider Handle */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-green-400 cursor-ew-resize"
                  style={{ left: `${sliderPosition}%` }}
                  onMouseDown={(e) => {
                    const handleMouseMove = (e: MouseEvent) => {
                      const rect = e.currentTarget?.parentElement?.getBoundingClientRect();
                      if (rect) {
                        const position = ((e.clientX - rect.left) / rect.width) * 100;
                        setSliderPosition(Math.max(0, Math.min(100, position)));
                      }
                    };

                    const handleMouseUp = () => {
                      document.removeEventListener('mousemove', handleMouseMove);
                      document.removeEventListener('mouseup', handleMouseUp);
                    };

                    document.addEventListener('mousemove', handleMouseMove);
                    document.addEventListener('mouseup', handleMouseUp);
                  }}
                >
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-green-400 rounded-full flex items-center justify-center">
                    <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-black" />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Image Info */}
      <div className="flex items-center justify-between text-sm text-gray-400">
        <div>
          {viewMode === 'original' && 'Original image'}
          {viewMode === 'overlay' && 'Segmentation overlay'}
          {viewMode === 'comparison' && 'Before/After comparison'}
        </div>
        <div>
          Drag slider to compare • Scroll to zoom • Click reset to restore
        </div>
      </div>
    </div>
  );
};

export default ImageViewer;
