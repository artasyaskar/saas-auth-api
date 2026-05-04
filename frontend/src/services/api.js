import axios from 'axios'

const API_BASE_URL = 'http://localhost:8002'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth-storage')
    if (token) {
      const authData = JSON.parse(token)
      if (authData.state?.token) {
        config.headers.Authorization = `Bearer ${authData.state.token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API endpoints
export const authAPI = {
  login: (credentials) => {
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  
  register: (userData) => api.post('/auth/register', userData),
  
  getCurrentUser: (token) => {
    return api.get('/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  },
  
  refreshToken: (refreshToken) => 
    api.post(`/auth/refresh?refresh_token=${refreshToken}`),
}

// User API endpoints
export const userAPI = {
  getProfile: () => api.get('/users/profile'),
  getUsage: () => api.get('/users/usage'),
  updateProfile: (userData) => api.put('/users/profile', userData),
}

// Admin API endpoints
export const adminAPI = {
  getUsers: () => api.get('/admin/users'),
  getUserStats: () => api.get('/admin/stats'),
  updateUserRole: (userId, role) => 
    api.put(`/admin/users/${userId}/role`, { role }),
  suspendUser: (userId) => 
    api.put(`/admin/users/${userId}/suspend`),
}

// Health check
export const healthAPI = {
  check: () => api.get('/health'),
}

export default api
