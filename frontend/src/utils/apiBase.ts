/** 空字符串 = 同源，走 Vite dev proxy；生产可设 VITE_API_BASE */
export const API_BASE = import.meta.env.VITE_API_BASE ?? '';
