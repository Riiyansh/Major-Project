import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (email, password) => {
    const response = await api.post('/api/register', { email, password });
    return response.data;
  },
  
  login: async (email, password) => {
    const response = await api.post('/api/login', { email, password });
    return response.data;
  },
  
  getMe: async () => {
    const response = await api.get('/api/me');
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  sendMessage: async (message, sessionId = null) => {
    const response = await api.post('/api/chat', { 
      user: message, 
      top_k: 3,
      session_id: sessionId 
    });
    return response.data;
  },
  
  getSessions: async () => {
    const response = await api.get('/api/chat/sessions');
    return response.data;
  },
  
  createSession: async (title = 'New Chat') => {
    const response = await api.post('/api/chat/sessions', { title });
    return response.data;
  },
  
  getSessionMessages: async (sessionId) => {
    const response = await api.get(`/api/chat/sessions/${sessionId}/messages`);
    return response.data;
  },
  
  deleteSession: async (sessionId) => {
    const response = await api.delete(`/api/chat/sessions/${sessionId}`);
    return response.data;
  },
};

// Legacy function for backward compatibility
export async function sendMessage(text) {
  const response = await chatAPI.sendMessage(text);
  return response;
}
