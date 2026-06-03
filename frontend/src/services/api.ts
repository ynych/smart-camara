import axios from 'axios';

const API_BASE = '';

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
export const generateLookbook = (requirementId: string) => api.post('/api/lookbook/generate', { requirement_id: requirementId });
export const getTasks = (status?: string) => api.get('/api/lookbook/tasks', { params: { status } });
export const getTask = (id: string) => api.get(`/api/lookbook/tasks/${id}`);
export const getGallery = () => api.get('/api/lookbook/gallery');

// Config API
export const getConfig = () => api.get('/api/config');
export const updateConfig = (data: any) => api.put('/api/config', data);
export const testConfig = () => api.post('/api/config/test');

// 素材管理API
export const listMaterials = (category?: string) => api.get('/api/materials', { params: { category } });
export const uploadMaterials = (files: FormData) => api.post('/api/materials/upload', files, { headers: { 'Content-Type': 'multipart/form-data' } });
export const deleteMaterial = (id: string) => api.delete(`/api/materials/${id}`);
export const scanMaterials = () => api.get('/api/materials/scan');

// 任务管理API
export const getTaskList = () => api.get('/api/lookbook/tasks');
export const deleteTask = (id: string) => api.delete(`/api/lookbook/tasks/${id}`);

export default api;
