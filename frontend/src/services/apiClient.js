import { authToken, logout } from './authService'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export async function apiRequest(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (authToken.value) {
    headers.Authorization = `Bearer ${authToken.value}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  // Automatically clear stale session if backend rejects the token
  if (response.status === 401) {
    logout()
    window.location.href = '/login'
    throw new Error('Session expired. Please sign in again.')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed (${response.status})`
    throw new Error(message)
  }

  return data
}