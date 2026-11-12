import { authToken, logout } from './authService'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export async function apiRequest(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (authToken.value) {
    headers.Authorization = `Bearer ${authToken.value}`
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(`Cannot reach the API at ${API_BASE_URL}. Check that the backend is running.`)
  }

  // Automatically clear stale session if backend rejects the token
  if (response.status === 401 && authToken.value) {
    logout()
    window.location.href = '/login'
    throw new Error('Session expired. Please sign in again.')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = data?.detail || data?.message
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join('; ')
        : `Request failed (${response.status})`
    throw new Error(message)
  }

  return data
}
