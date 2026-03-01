import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export interface AnalysisResponse {
  metrics: {
    root_length_mm: number;
    stem_length_mm: number;
    leaf_area_mm2: number;
    root_area_mm2: number;
    stem_area_mm2?: number;
  };
  overlay: string;
  confidence: number;
  loaded_num_classes?: number;
  class_names?: string[];
  loaded_model_type?: 'unet' | 'yolo' | string;
}

export const analyzeImage = async (
  file: File,
  modelType: 'unet' | 'yolo' = 'unet',
): Promise<AnalysisResponse> => {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('model_type', modelType);

  const response = await apiClient.post('/api/predict', formData);

  return response.data;
};

export default apiClient;
