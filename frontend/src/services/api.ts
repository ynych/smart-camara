import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8155';

const api = axios.create({ baseURL: API_BASE });

// Lookbook API
export const uploadSourceImage = (file: File, description?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  if (description) formData.append('description', description);
  return api.post('/api/lookbook/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
};

export const getRequirements = (status?: string) => api.get('/api/lookbook/requirements', { params: { status } });
export const getRequirement = (id: string) => api.get(`/api/lookbook/requirements/${id}`);
export const updateRequirement = (id: string, data: any) => api.put(`/api/lookbook/requirements/${id}`, data);
export const analyzeRequirement = (id: string, description?: string) => api.post(`/api/lookbook/requirements/${id}/analyze`, { description });
export const getStyles = () => api.get('/api/lookbook/styles');
export const generateLookbook = (data: {
    requirement_id?: string;
    model_id?: string;
    clothing_ids?: string[];
    reference_id?: string;
    scene_id?: string;
    size?: string;
    quantity?: number;
    prompts?: any[];
    acceptance_criteria?: string;
    business_context?: any;
    reference_image_path?: string;
}) => api.post('/api/lookbook/generate', data);
export const getTasks = (status?: string) => api.get('/api/lookbook/tasks', { params: { status } });
export const getTask = (id: string) => api.get(`/api/lookbook/tasks/${id}`);
export type GalleryFilters = {
  task_id?: string;
  model_id?: string;
  clothing_id?: string;
  reference_id?: string;
};

export const getGallery = (filters?: GalleryFilters) =>
  api.get('/api/lookbook/gallery', { params: filters || {} });

// Config API
export const getConfig = () => api.get('/api/config');
export const updateConfig = (data: any) => api.put('/api/config', data);
export const testConfig = () => api.post('/api/config/test');
export const testChatConfig = () => api.post('/api/config/test-chat');

// 素材管理API
export const listMaterials = (category?: string) => api.get('/api/materials', { params: { category } });
export const uploadMaterials = (files: FormData) => api.post('/api/materials/upload', files, { headers: { 'Content-Type': 'multipart/form-data' } });
export const deleteMaterial = (id: string) => api.delete(`/api/materials/${id}`);
export const scanMaterials = () => api.get('/api/materials/scan');

// 素材管理 - content目录
export const scanContentMaterials = () => api.get('/api/materials/scan');
export const getGroupedMaterials = (params?: {
  sections?: string;
  outfit_set?: string;
  shoot_type?: string;
}) => api.get('/api/materials/grouped', { params: params || undefined });
export const rebuildThumbnails = () => api.post('/api/materials/thumbnails/rebuild');
export const checkClothingConflict = (items: any[]) =>
    api.post('/api/materials/check-conflict', { items });

// Lookbook - 新增
export const generatePrompt = (data: {
    model_id: string;
    clothing_ids: string[];
    reference_id: string;
    scene_id?: string;
    quantity: number;
    size?: string;
    business_context?: any;
    acceptance_criteria?: string;
}) => api.post('/api/lookbook/generate-prompt', data);

// 任务管理API
export const getTaskList = () => api.get('/api/lookbook/tasks');
export const deleteTask = (id: string) => api.delete(`/api/lookbook/tasks/${id}`);
export const reviewGeneratedImage = (id: string, status: 'approved' | 'rejected', feedback?: string) =>
    api.post(`/api/lookbook/images/${id}/review`, { status, feedback });

// Harness & 评价 API
export const getHarnessTools = () => api.get('/api/harness/tools');
export const runHarnessTool = (toolId: string, context: Record<string, unknown>) =>
  api.post(`/api/harness/tools/${toolId}/run`, { context });
export const getHarnessPipeline = (pipelineId = 'lookbook_v1') =>
  api.get('/api/harness/pipeline', { params: { pipeline_id: pipelineId } });
export const runHarnessPipeline = (data: {
  context: Record<string, unknown>;
  enabled_modules?: string[];
  include_regen?: boolean;
}) => api.post('/api/harness/pipeline/run', data);
export const runHarnessModule = (moduleId: string, context: Record<string, unknown>) =>
  api.post(`/api/harness/pipeline/module/${moduleId}/run`, { context });
export const getHarnessContext = (imageId: string) => api.get(`/api/harness/context/${imageId}`);

export const getEvaluation = (imageId: string) => api.get(`/api/evaluations/${imageId}`);
export const saveEvaluation = (imageId: string, data: Record<string, unknown>) =>
  api.post(`/api/evaluations/${imageId}`, data);
export const generateAiEvaluation = (imageId: string) => api.post(`/api/evaluations/${imageId}/ai-draft`);
export const optimizeImagePrompt = (imageId: string, confirmedPrompt?: string) =>
  api.post(`/api/images/${imageId}/optimize-prompt`, confirmedPrompt ? { confirmed_prompt: confirmedPrompt } : {});
export const regenerateImage = (imageId: string, prompt: string) =>
  api.post(`/api/images/${imageId}/regenerate`, { prompt });

// Legacy exports kept so inactive pages still type-check.
export const getScenes = () => api.get('/api/scenes');
export const createScene = (data: any) => api.post('/api/scenes', data);
export const updateScene = (id: string, data: any) => api.put(`/api/scenes/${id}`, data);
export const deleteScene = (id: string) => api.delete(`/api/scenes/${id}`);
export const getMaterials = (params?: any) => api.get('/api/materials', { params });
export const getClothingNames = () => api.get('/api/materials/clothing-names');
export const previewPrompt = (data: any) => api.post('/api/generate/preview-prompt', data);
export const createGenerationTask = (data: any) => api.post('/api/generate', data);
export const getTaskStatus = (id: string) => api.get(`/api/generate/tasks/${id}/status`);
export const retryTask = (id: string) => api.post(`/api/generate/tasks/${id}/retry`);
export const executeTask = (id: string) => api.post(`/api/generate/tasks/${id}/execute`);
export const getReviewImages = (params?: any) => api.get('/api/review/images', { params });
export const approveImage = (id: string) => reviewGeneratedImage(id, 'approved');
export const rejectImage = (id: string, feedback: string) => reviewGeneratedImage(id, 'rejected', feedback);
export const getReviewStats = () => api.get('/api/review/stats');
export const getDeliveries = (params?: any) => api.get('/api/deliveries', { params });
export const createDelivery = (data: any) => api.post('/api/deliveries', data);
export const updateDelivery = (id: string, data: any) => api.put(`/api/deliveries/${id}`, data);
export const deleteDelivery = (id: string) => api.delete(`/api/deliveries/${id}`);
export const regenerateDelivery = (id: string) => api.post(`/api/deliveries/${id}/regenerate`);
export const approveDelivery = (id: string) => api.post(`/api/deliveries/${id}/approve`);
export const rejectDelivery = (id: string, feedback: string) => api.post(`/api/deliveries/${id}/reject`, { feedback });

export default api;
