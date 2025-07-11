import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (credentials) => api.post('/api/auth/login', credentials),
  register: (userData) => api.post('/api/auth/register', userData),
  logout: () => api.post('/api/auth/logout'),
  getProfile: () => api.get('/api/auth/me'),
  updateProfile: (data) => api.put('/api/auth/me', data),
  refreshToken: () => api.post('/api/auth/refresh'),
};

export const pipelinesAPI = {
  getAll: (params) => api.get('/api/pipelines', { params }),
  getById: (id) => api.get(`/api/pipelines/${id}`),
  create: (data) => api.post('/api/pipelines', data),
  update: (id, data) => api.put(`/api/pipelines/${id}`, data),
  delete: (id) => api.delete(`/api/pipelines/${id}`),
  getRuns: (id, params) => api.get(`/api/pipelines/${id}/runs`, { params }),
  getRun: (pipelineId, runId) => api.get(`/api/pipelines/${pipelineId}/runs/${runId}`),
  trigger: (id, data) => api.post(`/api/pipelines/${id}/trigger`, data),
  getMetrics: (id, params) => api.get(`/api/pipelines/${id}/metrics`, { params }),
};

export const monitoringAPI = {
  getDataSources: (params) => api.get('/api/monitoring/data-sources', { params }),
  getDataSource: (id) => api.get(`/api/monitoring/data-sources/${id}`),
  createDataSource: (data) => api.post('/api/monitoring/data-sources', data),
  updateDataSource: (id, data) => api.put(`/api/monitoring/data-sources/${id}`, data),
  deleteDataSource: (id) => api.delete(`/api/monitoring/data-sources/${id}`),
  testConnection: (id) => api.post(`/api/monitoring/data-sources/${id}/test-connection`),
  
  getHealthChecks: (params) => api.get('/api/monitoring/health-checks', { params }),
  getHealthCheck: (id) => api.get(`/api/monitoring/health-checks/${id}`),
  createHealthCheck: (data) => api.post('/api/monitoring/health-checks', data),
  getHealthCheckResults: (id, params) => api.get(`/api/monitoring/health-checks/${id}/results`, { params }),
  runHealthCheck: (id) => api.post(`/api/monitoring/health-checks/${id}/run`),
};

export const alertsAPI = {
  getAlertRules: (params) => api.get('/api/alerts/rules', { params }),
  getAlertRule: (id) => api.get(`/api/alerts/rules/${id}`),
  createAlertRule: (data) => api.post('/api/alerts/rules', data),
  updateAlertRule: (id, data) => api.put(`/api/alerts/rules/${id}`, data),
  deleteAlertRule: (id) => api.delete(`/api/alerts/rules/${id}`),
  
  getAlerts: (params) => api.get('/api/alerts', { params }),
  getAlert: (id) => api.get(`/api/alerts/${id}`),
  acknowledgeAlert: (id) => api.post(`/api/alerts/${id}/acknowledge`),
  resolveAlert: (id) => api.post(`/api/alerts/${id}/resolve`),
  getAlertHistory: (id) => api.get(`/api/alerts/${id}/history`),
};

export const dashboardAPI = {
  getOverview: (params) => api.get('/api/dashboard/overview', { params }),
  getPipelineHealth: () => api.get('/api/dashboard/pipeline-health'),
  getDataSourceHealth: () => api.get('/api/dashboard/data-source-health'),
  getRecentActivity: () => api.get('/api/dashboard/recent-activity'),
  getMetrics: (params) => api.get('/api/dashboard/metrics', { params }),
  getTopPipelines: (params) => api.get('/api/dashboard/top-pipelines', { params }),
};

export const usersAPI = {
  getAll: (params) => api.get('/api/users', { params }),
  getById: (id) => api.get(`/api/users/${id}`),
  create: (data) => api.post('/api/users', data),
  update: (id, data) => api.put(`/api/users/${id}`, data),
  delete: (id) => api.delete(`/api/users/${id}`),
  getRoles: () => api.get('/api/users/roles'),
  getProfile: () => api.get('/api/users/profile'),
  updateProfile: (data) => api.put('/api/users/profile', data),
};

export default api; 