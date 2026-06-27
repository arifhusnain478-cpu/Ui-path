import axios from "axios";
import mockAdapter from "./mockAdapter.js";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

if (import.meta.env.VITE_USE_MOCK_API === "true") {
  apiClient.defaults.adapter = mockAdapter;
}

apiClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("qualitrace_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default apiClient;
