import axios from 'axios'

const resolveApiBaseUrl = () => {
  if (typeof window !== 'undefined' && window.location.port === '13001') {
    return 'http://localhost:18000'
  }
  return (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 'http://localhost:8000'
}

export const API_BASE_URL = resolveApiBaseUrl()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

/**
 * Fetch health status from FastAPI backend orchestrator
 */
export const getHealth = async () => {
  const response = await apiClient.get('/health')
  return response.data
}

/**
 * Placeholder for future cluster investigation service
 */
export const investigateCluster = async () => {
  console.info('[Placeholder] investigateCluster will trigger AI reasoning in Phase 2')
  return { status: 'placeholder' }
}
