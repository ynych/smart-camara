/**
 * 将 content/ 目录的绝对路径转为前端可访问的 URL
 * 输入: /workspace/content/模特卡/xxx.jpg
 * 输出: /content/%E6%A8%A1%E7%89%B9%E5%8D%A1/xxx.jpg
 */
import { API_BASE } from './apiBase';

export function toContentUrl(filePath: string): string {
  if (!filePath) return '';
  const contentIndex = filePath.indexOf('/content/');
  if (contentIndex >= 0) {
    const relativePath = filePath.substring(contentIndex + 1);
    const segments = relativePath.split('/');
    const encoded = segments.map(s => encodeURIComponent(s)).join('/');
    return `${API_BASE}/${encoded}`;
  }
  const assetsIndex = filePath.indexOf('/assets/');
  if (assetsIndex >= 0) {
    const relativePath = filePath.substring(assetsIndex + 1);
    const segments = relativePath.split('/');
    const encoded = segments.map(s => encodeURIComponent(s)).join('/');
    return `${API_BASE}/${encoded}`;
  }
  if (filePath.startsWith('/uploads/')) return `${API_BASE}/assets${filePath}`;
  if (filePath.startsWith('/generated/')) return `${API_BASE}/assets${filePath}`;
  if (filePath.startsWith('http') || filePath.startsWith('data:')) return filePath;
  if (filePath.startsWith('/')) return filePath;
  return filePath;
}
