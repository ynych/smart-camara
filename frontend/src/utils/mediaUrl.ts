import { toContentUrl } from './contentUrl';

export interface MediaItem {
  file_path?: string;
  path?: string;
  thumbnail_path?: string;
}

/** 列表展示用缩略图，预览用原图 */
export function toMediaUrl(item: MediaItem | string | null | undefined, full = false): string {
  if (!item) return '';
  if (typeof item === 'string') return toContentUrl(item);
  if (!full && item.thumbnail_path) return toContentUrl(item.thumbnail_path);
  return toContentUrl(item.file_path || item.path || '');
}

export function mediaPreview(item: MediaItem | null | undefined) {
  const src = toMediaUrl(item, true);
  return src ? { src } : false;
}
