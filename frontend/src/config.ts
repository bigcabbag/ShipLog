/** 空字符串 = 同源（Docker nginx 或 Vite dev proxy）；直连后端时在 .env 设完整 URL */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
