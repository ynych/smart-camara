import axios from 'axios';

import { API_BASE } from '../utils/apiBase';

const adminApi = axios.create({ baseURL: API_BASE });

export const adminList = (path: string) => adminApi.get(path).then((r) => r.data.items ?? r.data);
export const adminGet = (path: string, id: string) => adminApi.get(`${path}/${id}`).then((r) => r.data);
export const adminCreate = (path: string, data: Record<string, unknown>) => adminApi.post(path, data).then((r) => r.data);
export const adminUpdate = (path: string, id: string, data: Record<string, unknown>) =>
  adminApi.put(`${path}/${id}`, data).then((r) => r.data);
export const adminDelete = (path: string, id: string) => adminApi.delete(`${path}/${id}`).then((r) => r.data);

export const getDefaultAgent = () => adminApi.get('/api/agent-runtime/agents/default').then((r) => r.data);
export const invokeAgent = (agentId: string, inputs: Record<string, unknown>) =>
  adminApi.post(`/api/agent-runtime/agents/${agentId}/invoke`, inputs).then((r) => r.data);
export const runAgentTestCase = (agentId: string, caseId: string) =>
  adminApi.post(`/api/agent-runtime/agents/${agentId}/test-cases/${caseId}/run`).then((r) => r.data);
export const chatAgent = (agentId: string, message: string, sessionId?: string) =>
  adminApi.post(`/api/agent-runtime/agents/${agentId}/chat`, { message, session_id: sessionId }).then((r) => r.data);
export const runGoldenRegression = (body: Record<string, unknown>) =>
  adminApi.post('/api/agent-runtime/golden/regression', body).then((r) => r.data);
export const importGoldenFromEval = (imageId: string) =>
  adminApi.post(`/api/admin/golden-cases/import-from-evaluation/${imageId}`).then((r) => r.data);
export const runHarnessTestcasePrompts = (caseId: string) =>
  adminApi.post(`/api/agent-runtime/harness-testcases/${caseId}/run-prompts`).then((r) => r.data);
export const runHarnessTestcaseImages = (caseId: string) =>
  adminApi.post(`/api/agent-runtime/harness-testcases/${caseId}/run-images`).then((r) => r.data);
export const runHarnessTestcaseEvaluation = (caseId: string) =>
  adminApi.post(`/api/agent-runtime/harness-testcases/${caseId}/run-evaluation`).then((r) => r.data);
export const syncPromptfooTests = () =>
  adminApi.post('/api/agent-runtime/promptfoo/sync').then((r) => r.data);
export const getOptimizationModules = () =>
  adminApi.get('/api/agent-runtime/modules').then((r) => r.data);

export const importHarnessFromEvaluation = (imageId: string) =>
  adminApi.post(`/api/admin/harness-testcases/import-from-evaluation/${imageId}`).then((r) => r.data);

export const getPipelineVersions = (slug = 'lookbook_v1') =>
  adminApi.get('/api/agent-runtime/pipeline/versions', { params: { slug } }).then((r) => r.data);

export const clonePipelineDraft = (slug = 'lookbook_v1') =>
  adminApi.post('/api/agent-runtime/pipeline/versions/clone-draft', null, { params: { slug } }).then((r) => r.data);

export const publishPipelineDraft = (slug = 'lookbook_v1') =>
  adminApi.post('/api/agent-runtime/pipeline/versions/publish', null, { params: { slug } }).then((r) => r.data);

export const rejectPipelineDraft = (slug = 'lookbook_v1') =>
  adminApi.post('/api/agent-runtime/pipeline/versions/reject', null, { params: { slug } }).then((r) => r.data);

export const updatePipelineDraftModules = (modules: Record<string, unknown>, slug = 'lookbook_v1') =>
  adminApi.put('/api/agent-runtime/pipeline/versions/draft/modules', { modules }, { params: { slug } }).then((r) => r.data);

export const comparePipelineVersions = (body: { slug?: string; testcase_ids?: string[] }) =>
  adminApi.post('/api/agent-runtime/pipeline/versions/compare', { slug: 'lookbook_v1', ...body }).then((r) => r.data);

export default adminApi;
