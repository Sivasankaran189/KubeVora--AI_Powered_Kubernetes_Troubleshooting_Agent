import axios from 'axios'

// Dynamically resolve API URL:
// - If loaded on host port 13001 (kind NodePort), talk to backend on 18000
// - Otherwise use VITE_API_URL or http://localhost:8000/api/v1
const resolveBaseUrl = () => {
  if (typeof window !== 'undefined' && window.location.port === '13001') {
    return 'http://localhost:18000/api/v1'
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
}

const client = axios.create({
  baseURL: resolveBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

// Request Interceptor: Attach Authorization Bearer token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('kubevora_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response Interceptor: Handle 401 Unauthorized globally
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isAuthEndpoint = error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/register')
      if (!isAuthEndpoint) {
        localStorage.removeItem('kubevora_token')
        localStorage.removeItem('kubevora_user')
        if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
          window.location.href = '/login?expired=true'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
