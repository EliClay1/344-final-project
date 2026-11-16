import { ref } from 'vue'
import { apiRequest, USE_MOCK } from './apiClient'

const STORAGE_KEY = 'cyber344_auth'
const MOCK_USERS_KEY = 'cyber344_mock_users'
const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,32}$/

const savedAuth = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
const validSavedAuth = savedAuth?.mock === USE_MOCK ? savedAuth : null

export const currentUser = ref(validSavedAuth?.user || null)
export const authToken = ref(validSavedAuth?.token || null)

function getMockUsers() {
  const defaultUsers = [
    { id: 1, username: 'admin', password: 'password123', permission_level: 2 },
    { id: 2, username: 'dixon', password: 'password123', permission_level: 0 },
    { id: 3, username: 'andrew', password: 'password123', permission_level: 0 },
  ]
  const stored = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || 'null')
  return stored || defaultUsers
}

function saveSession(authData) {
  currentUser.value = authData.user
  authToken.value = authData.token
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...authData, mock: USE_MOCK }))
}

export async function login(username, password) {
  const cleanUser = username.trim()
  if (!cleanUser || !password) {
    throw new Error('Username and password are required.')
  }
  if (cleanUser.length > 32 || password.length > 128) {
    throw new Error('Username or password exceeds maximum length.')
  }

  let authData

  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 300))
    const users = getMockUsers()
    const existing = users.find(
      (u) => u.username.toLowerCase() === cleanUser.toLowerCase()
    )

    if (!existing || existing.password !== password) {
      throw new Error('Invalid username or password.')
    }

    authData = {
      token: 'mock-jwt-token-' + Date.now(),
      user: {
        id: existing.id,
        username: existing.username,
        permission_level: existing.permission_level ?? (existing.role === 'admin' ? 2 : 0),
      },
    }
  } else {
    authData = await apiRequest('/login', {
      method: 'POST',
      body: JSON.stringify({
        username: cleanUser,
        password,
      }),
    })
  }

  saveSession(authData)
  return authData.user
}

export async function register(username, password) {
  const cleanUser = username.trim()

  if (!USERNAME_REGEX.test(cleanUser)) {
    throw new Error(
      'Username must be 3–32 characters using only letters, numbers, or underscores.'
    )
  }
  const passwordBytes = new TextEncoder().encode(password).length
  if (passwordBytes < 8 || passwordBytes > 72) {
    throw new Error('Password must be between 8 and 72 bytes.')
  }

  let authData

  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 350))
    const users = getMockUsers()

    const duplicate = users.some(
      (u) => u.username.toLowerCase() === cleanUser.toLowerCase()
    )
    if (duplicate) {
      throw new Error('That username is already taken.')
    }

    // Always default self-registered accounts to Base User ("user")
    const newUser = {
      id: users.length + 1,
      username: cleanUser,
      password,
      permission_level: 0,
    }

    users.push(newUser)
    localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users))

    authData = {
      token: 'mock-jwt-token-' + Date.now(),
      user: {
        id: newUser.id,
        username: newUser.username,
        permission_level: newUser.permission_level,
      },
    }
  } else {
    await apiRequest('/users', {
      method: 'POST',
      body: JSON.stringify({
        username: cleanUser,
        password,
      }),
    })
    return login(cleanUser, password)
  }

  saveSession(authData)
  return authData.user
}

export function logout() {
  currentUser.value = null
  authToken.value = null
  localStorage.removeItem(STORAGE_KEY)
}

export function isAuthenticated() {
  return Boolean(authToken.value && currentUser.value)
}

export function isAdmin() {
  return currentUser.value?.permission_level === 2
}
