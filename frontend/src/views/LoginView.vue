<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../services/authService'
import { USE_MOCK as isMockMode } from '../services/apiClient'

const router = useRouter()

const isRegisterMode = ref(false)
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

function toggleMode() {
  isRegisterMode.value = !isRegisterMode.value
  error.value = ''
  password.value = ''
  confirmPassword.value = ''
}

function fillDemo(role) {
  isRegisterMode.value = false
  error.value = ''
  username.value = role === 'admin' ? 'admin' : 'dixon'
  password.value = 'password123'
}

async function handleSubmit() {
  error.value = ''

  if (isRegisterMode.value && password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }

  loading.value = true

  try {
    if (isRegisterMode.value) {
      await register(username.value, password.value)
    } else {
      await login(username.value, password.value)
    }
    router.push('/dashboard')
  } catch (err) {
    error.value = err.message || 'Authentication failed.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <section class="auth-panel" aria-labelledby="auth-title">
      <h1 id="auth-title">{{ isRegisterMode ? 'Create an account' : 'Sign in' }}</h1>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label for="username">Username</label>
          <input id="username" v-model="username" type="text" maxlength="32" autocomplete="username" required />
        </div>
        <div class="form-field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" maxlength="128" :autocomplete="isRegisterMode ? 'new-password' : 'current-password'" required />
        </div>
        <div v-if="isRegisterMode" class="form-field">
          <label for="confirm-password">Confirm password</label>
          <input id="confirm-password" v-model="confirmPassword" type="password" maxlength="128" autocomplete="new-password" required />
        </div>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary-button auth-submit" type="submit" :disabled="loading">{{ loading ? (isRegisterMode ? 'Creating account…' : 'Signing in…') : (isRegisterMode ? 'Create account' : 'Sign in') }}</button>
      </form>

      <p class="auth-switch">{{ isRegisterMode ? 'Already have an account?' : 'Need an account?' }} <button type="button" @click="toggleMode">{{ isRegisterMode ? 'Sign in' : 'Register' }}</button></p>

      <div v-if="isMockMode" class="demo-box">
        <h2>Demo accounts</h2>
        <p>Both accounts use <code>password123</code>.</p>
        <div><button type="button" @click="fillDemo('user')">Use dixon</button><button type="button" @click="fillDemo('admin')">Use admin</button></div>
      </div>
    </section>
  </div>
</template>
