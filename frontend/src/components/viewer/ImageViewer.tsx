import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, RotateCw } from 'lucide-react';

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
  const [viewMode, setViewMode] = useState<'original' | 'overlay'>('original');
  const [zoom, setZoom] = useState(1);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragStateRef = useRef<{ dragging: boolean; startX: number; startY: number; baseX: number; baseY: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const zoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 4));
  const zoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.5));
  const resetView = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  const clampOffsetToBounds = (nextOffset: { x: number; y: number }, nextZoom: number) => {
    const el = containerRef.current;
    if (!el) return nextOffset;

    const rect = el.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;

    const scaledW = w * nextZoom;
    const scaledH = h * nextZoom;

    const minVisible = 48;

    const maxX = Math.max(0, (scaledW - w) / 2 + (w / 2 - minVisible));
    const maxY = Math.max(0, (scaledH - h) / 2 + (h / 2 - minVisible));

    const clampedX = Math.max(-maxX, Math.min(maxX, nextOffset.x));
    const clampedY = Math.max(-maxY, Math.min(maxY, nextOffset.y));

    return { x: clampedX, y: clampedY };
  };

  useEffect(() => {
    const onZoomIn = () => zoomIn();
    const onZoomOut = () => zoomOut();
    const onReset = () => resetView();

    window.addEventListener('viewer:zoomIn', onZoomIn as EventListener);
    window.addEventListener('viewer:zoomOut', onZoomOut as EventListener);
    window.addEventListener('viewer:reset', onReset as EventListener);

    return () => {
      window.removeEventListener('viewer:zoomIn', onZoomIn as EventListener);
      window.removeEventListener('viewer:zoomOut', onZoomOut as EventListener);
      window.removeEventListener('viewer:reset', onReset as EventListener);
    };
  }, []);

  const transformStyle = useMemo(() => {
    return {
      transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
      transformOrigin: 'center center',
    } as React.CSSProperties;
  }, [offset.x, offset.y, zoom]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY;
    if (delta > 0) {
      zoomOut();
    } else {
      zoomIn();
    }
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (!containerRef.current) return;
    if ((e.target as HTMLElement).closest('[data-viewer-control="true"]')) return;
    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
    dragStateRef.current = {
      dragging: true,
      startX: e.clientX,
      startY: e.clientY,
      baseX: offset.x,
      baseY: offset.y,
    };
    setIsDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const st = dragStateRef.current;
    if (!st || !st.dragging) return;
    const dx = e.clientX - st.startX;
    const dy = e.clientY - st.startY;
    setOffset(clampOffsetToBounds({ x: st.baseX + dx, y: st.baseY + dy }, zoom));
  };

  const stopDragging = () => {
    if (dragStateRef.current) {
      dragStateRef.current.dragging = false;
    }
    setIsDragging(false);
  };

  return (
    <div className="space-y-4">
      {/* View Mode Controls */}
      <div className="viewer-toolbar" data-viewer-control="true">
        <div className="viewer-toolbar__group" data-viewer-control="true">
          <button
            onClick={() => setViewMode('original')}
            className={`viewer-toolbar__tab ${viewMode === 'original' ? 'is-active' : ''}`}
            data-viewer-control="true"
          >
            <Eye size={14} />
            Оригинал
          </button>

          <button
            onClick={() => setViewMode('overlay')}
            disabled={!overlayImage || isAnalyzing}
            className={`viewer-toolbar__tab ${viewMode === 'overlay' ? 'is-active' : ''}`}
            data-viewer-control="true"
          >
            <EyeOff size={14} />
            Сегментация
          </button>
        </div>

        <div className="viewer-toolbar__group" data-viewer-control="true">
          <button onClick={zoomOut} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Отдалить">−</button>
          <span className="viewer-toolbar__zoom" data-viewer-control="true">{Math.round(zoom * 100)}%</span>
          <button onClick={zoomIn} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Приблизить">+</button>
          <button onClick={resetView} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Сброс">
            <RotateCw size={14} />
          </button>
        </div>
      </div>

      {/* Image Display */}
      <div
        ref={containerRef}
        className="relative viewer-canvas overflow-hidden"
        style={{ height: '640px', touchAction: 'none', cursor: isDragging ? 'grabbing' : 'grab' }}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
        onLostPointerCapture={stopDragging}
      >
        {isAnalyzing ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <div className="w-16 h-16 border-4 border-green-400 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-gray-400">Выполняю анализ...</p>
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
                alt="Оригинальное изображение"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ ...transformStyle, pointerEvents: 'none', userSelect: 'none' }}
                draggable={false}
              />
            )}

            {viewMode === 'overlay' && overlayImage && (
              <motion.img
                key="overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                src={overlayImage}
                alt="Сегментация"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ ...transformStyle, pointerEvents: 'none', userSelect: 'none' }}
                draggable={false}
              />
            )}

          </div>
        )}
      </div>

      {/* Image Info */}
      <div className="flex items-center justify-between text-sm text-gray-400">
        <div>
          {viewMode === 'original' && 'Оригинал'}
          {viewMode === 'overlay' && 'Сегментация'}
        </div>
        <div>
          Колёсико: масштаб • Зажать и тянуть: перемещение
        </div>
      </div>
    </div>
  );
};

export default ImageViewer;
