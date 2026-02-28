import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, RotateCw, SlidersHorizontal } from 'lucide-react';

interface ImageViewerProps {
  originalImage: string;
  overlayImage?: string;
  isAnalyzing?: boolean;
}

type ViewerMode = 'original' | 'overlay' | 'comparison';

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const ImageViewer: React.FC<ImageViewerProps> = ({
  originalImage,
  overlayImage,
  isAnalyzing = false,
}) => {
  const [viewMode, setViewMode] = useState<ViewerMode>('original');
  const [comparePosition, setComparePosition] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [isScrubbing, setIsScrubbing] = useState(false);

  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [imageNaturalSize, setImageNaturalSize] = useState({ width: 1, height: 1 });

  const containerRef = useRef<HTMLDivElement | null>(null);
  const panStateRef = useRef<{ startX: number; startY: number; baseX: number; baseY: number } | null>(null);
  const scrubStateRef = useRef<{ startX: number; startCompare: number } | null>(null);

  const frameRect = useMemo(() => {
    const cw = containerSize.width;
    const ch = containerSize.height;
    const iw = imageNaturalSize.width;
    const ih = imageNaturalSize.height;

    if (cw <= 0 || ch <= 0 || iw <= 0 || ih <= 0) {
      return { left: 0, top: 0, width: cw, height: ch };
    }

    const containerAspect = cw / ch;
    const imageAspect = iw / ih;

    let width = cw;
    let height = ch;

    if (containerAspect > imageAspect) {
      height = ch;
      width = height * imageAspect;
    } else {
      width = cw;
      height = width / imageAspect;
    }

    return {
      left: (cw - width) / 2,
      top: (ch - height) / 2,
      width,
      height,
    };
  }, [containerSize.height, containerSize.width, imageNaturalSize.height, imageNaturalSize.width]);

  const zoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 4));
  const zoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.5));
  const resetView = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  const clampOffsetToBounds = (nextOffset: { x: number; y: number }, nextZoom: number) => {
    if (nextZoom <= 1) return { x: 0, y: 0 };

    const cw = containerSize.width;
    const ch = containerSize.height;
    const scaledW = frameRect.width * nextZoom;
    const scaledH = frameRect.height * nextZoom;

    const maxX = Math.max(0, (scaledW - cw) / 2 + 40);
    const maxY = Math.max(0, (scaledH - ch) / 2 + 40);

    return {
      x: clamp(nextOffset.x, -maxX, maxX),
      y: clamp(nextOffset.y, -maxY, maxY),
    };
  };

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setImageNaturalSize({
        width: Math.max(1, img.naturalWidth),
        height: Math.max(1, img.naturalHeight),
      });
    };
    img.src = originalImage;
  }, [originalImage]);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const updateSize = () => {
      setContainerSize({ width: el.clientWidth, height: el.clientHeight });
    };

    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!isAnalyzing && overlayImage) {
      setViewMode('overlay');
    }
  }, [isAnalyzing, overlayImage]);

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

  const layerTransformStyle = useMemo(
    () =>
      ({
        transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
        transformOrigin: 'center center',
      }) as React.CSSProperties,
    [offset.x, offset.y, zoom],
  );

  const onWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (isScrubbing) return;
    if (e.deltaY > 0) zoomOut();
    else zoomIn();
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const target = e.target as HTMLElement;

    if (viewMode === 'comparison' && target.closest('[data-compare-handle="true"]')) {
      scrubStateRef.current = { startX: e.clientX, startCompare: comparePosition };
      setIsScrubbing(true);
      e.currentTarget.setPointerCapture(e.pointerId);
      return;
    }

    if (target.closest('[data-viewer-control="true"]')) return;

    panStateRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      baseX: offset.x,
      baseY: offset.y,
    };
    setIsPanning(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isScrubbing && scrubStateRef.current) {
      const deltaX = e.clientX - scrubStateRef.current.startX;
      const baseWidth = Math.max(1, frameRect.width);
      const deltaPercent = (deltaX * 100) / (baseWidth * zoom);
      setComparePosition(clamp(scrubStateRef.current.startCompare + deltaPercent, 0, 100));
      return;
    }

    if (!isPanning || !panStateRef.current) return;
    const st = panStateRef.current;
    const dx = e.clientX - st.startX;
    const dy = e.clientY - st.startY;
    setOffset(clampOffsetToBounds({ x: st.baseX + dx, y: st.baseY + dy }, zoom));
  };

  const stopPointer = () => {
    setIsPanning(false);
    setIsScrubbing(false);
    panStateRef.current = null;
    scrubStateRef.current = null;
  };

  const cursor = isScrubbing ? 'col-resize' : isPanning ? 'grabbing' : 'grab';

  return (
    <div className="space-y-4">
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

          <button
            onClick={() => setViewMode('comparison')}
            disabled={!overlayImage || isAnalyzing}
            className={`viewer-toolbar__tab ${viewMode === 'comparison' ? 'is-active' : ''}`}
            data-viewer-control="true"
          >
            <SlidersHorizontal size={14} />
            Сравнение
          </button>
        </div>

        <div className="viewer-toolbar__group" data-viewer-control="true">
          <button onClick={zoomOut} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Отдалить">
            -
          </button>
          <span className="viewer-toolbar__zoom" data-viewer-control="true">
            {Math.round(zoom * 100)}%
          </span>
          <button onClick={zoomIn} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Приблизить">
            +
          </button>
          <button onClick={resetView} className="viewer-toolbar__icon" data-viewer-control="true" aria-label="Сброс">
            <RotateCw size={14} />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative viewer-canvas overflow-hidden"
        style={{ height: '640px', touchAction: 'none', cursor }}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={stopPointer}
        onPointerCancel={stopPointer}
        onLostPointerCapture={stopPointer}
      >
        {isAnalyzing ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
              <div className="w-16 h-16 border-4 border-green-400 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-gray-400">Выполняю анализ...</p>
            </motion.div>
          </div>
        ) : (
          <div className="relative w-full h-full overflow-hidden">
            <div
              className="absolute"
              style={{
                left: `${frameRect.left}px`,
                top: `${frameRect.top}px`,
                width: `${frameRect.width}px`,
                height: `${frameRect.height}px`,
                ...layerTransformStyle,
              }}
            >
              {viewMode === 'original' && (
                <motion.img
                  key="original"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  src={originalImage}
                  alt="Оригинальное изображение"
                  className="absolute inset-0 w-full h-full object-fill select-none pointer-events-none"
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
                  className="absolute inset-0 w-full h-full object-fill select-none pointer-events-none"
                  draggable={false}
                />
              )}

              {viewMode === 'comparison' && overlayImage && (
                <>
                  <motion.img
                    key="comparison-original"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    src={originalImage}
                    alt="Оригинал"
                    className="absolute inset-0 w-full h-full object-fill select-none pointer-events-none"
                    draggable={false}
                  />

                  <motion.img
                    key="comparison-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    src={overlayImage}
                    alt="Сегментация"
                    className="absolute inset-0 w-full h-full object-fill select-none pointer-events-none"
                    style={{ clipPath: `inset(0 ${100 - comparePosition}% 0 0)` }}
                    draggable={false}
                  />

                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-white/90 pointer-events-none z-10"
                    style={{ left: `${comparePosition}%`, transform: 'translateX(-50%)' }}
                  />

                  <button
                    type="button"
                    data-compare-handle="true"
                    className="absolute top-1/2 z-20 h-8 w-8 rounded-full bg-white/90 border border-gray-700 shadow flex items-center justify-center text-gray-900"
                    style={{ left: `${comparePosition}%`, transform: 'translate(-50%, -50%)', cursor: 'col-resize' }}
                    aria-label="Двигать разделитель сравнения"
                  >
                    <>
                      {'<'}
                      {'>'}
                    </>
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-sm text-gray-400">
        <div>
          {viewMode === 'original' && 'Оригинал'}
          {viewMode === 'overlay' && 'Сегментация'}
          {viewMode === 'comparison' && 'Сравнение'}
        </div>
        <div>Колёсико: масштаб • Зажать и тянуть: перемещение</div>
      </div>
    </div>
  );
};

export default ImageViewer;
