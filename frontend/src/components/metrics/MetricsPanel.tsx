import React from 'react';
import { motion } from 'framer-motion';

interface Metrics {
  root_length_mm?: number;
  stem_length_mm?: number;
  leaf_area_mm2?: number;
  root_area_mm2?: number;
  stem_area_mm2?: number;
}

interface MetricsPanelProps {
  metrics?: Metrics;
  confidence?: number;
  isAnalyzing?: boolean;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({
  metrics,
  confidence,
  isAnalyzing = false,
}) => {
  if (isAnalyzing) {
    return (
      <div className="analysis-metrics">
        <div className="analysis-metrics__block">
          <div className="analysis-metrics__row">
            <span className="analysis-metrics__label">Длина корня</span>
            <span className="analysis-metrics__dots" aria-hidden="true" />
            <span className="analysis-metrics__value">
              <span className="skeleton inline-block h-4 w-24 rounded" />
            </span>
          </div>
          <div className="analysis-metrics__row">
            <span className="analysis-metrics__label">Длина стебля</span>
            <span className="analysis-metrics__dots" aria-hidden="true" />
            <span className="analysis-metrics__value">
              <span className="skeleton inline-block h-4 w-24 rounded" />
            </span>
          </div>
          <div className="analysis-metrics__row">
            <span className="analysis-metrics__label">Площадь листьев</span>
            <span className="analysis-metrics__dots" aria-hidden="true" />
            <span className="analysis-metrics__value">
              <span className="skeleton inline-block h-4 w-24 rounded" />
            </span>
          </div>
          <div className="analysis-metrics__row">
            <span className="analysis-metrics__label">Площадь корня</span>
            <span className="analysis-metrics__dots" aria-hidden="true" />
            <span className="analysis-metrics__value">
              <span className="skeleton inline-block h-4 w-24 rounded" />
            </span>
          </div>
          <div className="analysis-metrics__row">
            <span className="analysis-metrics__label">Площадь стебля</span>
            <span className="analysis-metrics__dots" aria-hidden="true" />
            <span className="analysis-metrics__value">
              <span className="skeleton inline-block h-4 w-24 rounded" />
            </span>
          </div>
        </div>

        <div className="analysis-metrics__confidence">
          <div className="analysis-metrics__confidence-main">
            <span className="analysis-metrics__confidence-label">Достоверность</span>
            <span className="analysis-metrics__confidence-value">
              <span className="skeleton inline-block h-4 w-14 rounded" />
            </span>
          </div>
          <div className="analysis-metrics__confidence-sub">
            <span className="skeleton inline-block h-3 w-52 rounded" />
          </div>
        </div>
      </div>
    );
  }

  const formatValue = (value: number | undefined, unit: string) => {
    if (value === undefined || Number.isNaN(value)) {
      return '-';
    }
    return `${value.toFixed(1)} ${unit}`;
  };

  const confidenceText = (c: number) => {
    if (c >= 0.9) return 'Высокая достоверность сегментации';
    if (c >= 0.7) return 'Средняя достоверность сегментации';
    return 'Низкая достоверность, попробуйте повторить анализ';
  };

  return (
    <div className="analysis-metrics">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="analysis-metrics__block"
      >
        <div className="analysis-metrics__row">
          <span className="analysis-metrics__label">Длина корня</span>
          <span className="analysis-metrics__dots" aria-hidden="true" />
          <span className="analysis-metrics__value">{formatValue(metrics?.root_length_mm, 'mm')}</span>
        </div>
        <div className="analysis-metrics__row">
          <span className="analysis-metrics__label">Длина стебля</span>
          <span className="analysis-metrics__dots" aria-hidden="true" />
          <span className="analysis-metrics__value">{formatValue(metrics?.stem_length_mm, 'mm')}</span>
        </div>
        <div className="analysis-metrics__row">
          <span className="analysis-metrics__label">Площадь листьев</span>
          <span className="analysis-metrics__dots" aria-hidden="true" />
          <span className="analysis-metrics__value">{formatValue(metrics?.leaf_area_mm2, 'mm²')}</span>
        </div>
        <div className="analysis-metrics__row">
          <span className="analysis-metrics__label">Площадь корня</span>
          <span className="analysis-metrics__dots" aria-hidden="true" />
          <span className="analysis-metrics__value">{formatValue(metrics?.root_area_mm2, 'mm²')}</span>
        </div>
        <div className="analysis-metrics__row">
          <span className="analysis-metrics__label">Площадь стебля</span>
          <span className="analysis-metrics__dots" aria-hidden="true" />
          <span className="analysis-metrics__value">{formatValue(metrics?.stem_area_mm2, 'mm²')}</span>
        </div>
      </motion.div>

      {confidence !== undefined && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.05 }}
          className="analysis-metrics__confidence"
        >
          <div className="analysis-metrics__confidence-main">
            <span className="analysis-metrics__confidence-label">Достоверность:</span>
            <span className="analysis-metrics__confidence-value">{Math.round(confidence * 100)}%</span>
          </div>
          <div className="analysis-metrics__confidence-sub">{confidenceText(confidence)}</div>
        </motion.div>
      )}
    </div>
  );
};

export default MetricsPanel;
