import { create } from 'zustand';

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

interface AnalysisStore {
  currentAnalysis: AnalysisData | null;
  setCurrentAnalysis: (analysis: AnalysisData | null) => void;
  startAnalysis: (file: File) => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  currentAnalysis: null,
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  startAnalysis: (file) => {
    // Analysis logic will be implemented
    console.log('Starting analysis for:', file.name);
  }
}));
