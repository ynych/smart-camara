/** 将 axios 错误转为用户可读提示；网络错误时提示启动后端。 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const err = error as {
    code?: string;
    message?: string;
    response?: { status?: number; data?: { detail?: string } };
  };
  if (!err.response && (err.code === 'ERR_NETWORK' || err.message === 'Network Error')) {
    return `${fallback}：后端未启动，请运行 ./start.sh restart`;
  }
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return `${fallback}：${detail}`;
  }
  if (err.message) return `${fallback}：${err.message}`;
  return fallback;
}
