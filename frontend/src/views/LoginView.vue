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
  <div class="max-w-md mx-auto mt-12 bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-1">
      {{ isRegisterMode ? 'Create Account' : 'Sign In' }}
    </h2>
    <p class="text-sm text-gray-500 mb-6">
      {{
        isRegisterMode
          ? 'Register a Base User account to submit and track tasks.'
          : 'Log in to submit URLs and monitor Kubernetes tasks.'
      }}
    </p>

    <form
      @submit.prevent="handleSubmit"
      class="space-y-4"
    >
      <div>
        <label
          for="username"
          class="block mb-2 font-medium"
        >
          Username
        </label>
        <input
          id="username"
          v-model="username"
          type="text"
          maxlength="32"
          autocomplete="username"
          placeholder="Enter username"
          required
          class="w-full border border-gray-300 rounded px-4 py-2"
        />
      </div>

      <div>
        <label
          for="password"
          class="block mb-2 font-medium"
        >
          Password
        </label>
        <input
          id="password"
          v-model="password"
          type="password"
          maxlength="128"
          :autocomplete="isRegisterMode ? 'new-password' : 'current-password'"
          placeholder="••••••••"
          required
          class="w-full border border-gray-300 rounded px-4 py-2"
        />
      </div>

      <div v-if="isRegisterMode">
        <label
          for="confirm-password"
          class="block mb-2 font-medium"
        >
          Confirm Password
        </label>
        <input
          id="confirm-password"
          v-model="confirmPassword"
          type="password"
          maxlength="128"
          autocomplete="new-password"
          placeholder="••••••••"
          required
          class="w-full border border-gray-300 rounded px-4 py-2"
        />
      </div>

      <p
        v-if="error"
        class="text-red-600 text-sm"
        role="alert"
      >
        {{ error }}
      </p>

      <button
        type="submit"
        :disabled="loading"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded font-medium"
      >
        {{
          loading
            ? isRegisterMode
              ? 'Creating account...'
              : 'Signing in...'
            : isRegisterMode
              ? 'Create Account'
              : 'Sign In'
        }}
      </button>
    </form>

    <div class="mt-4 text-center text-sm text-gray-600">
      <span>
        {{ isRegisterMode ? 'Already have an account?' : "Don't have an account?" }}
      </span>
      <button
        type="button"
        @click="toggleMode"
        class="ml-1 text-blue-600 hover:text-blue-800 font-medium"
      >
        {{ isRegisterMode ? 'Sign In' : 'Register' }}
      </button>
    </div>

    <div
      v-if="isMockMode"
      class="mt-6 pt-4 border-t border-gray-200"
    >
      <p class="text-xs text-gray-500 mb-2">
        Mock Demo Quick-Fill:
      </p>
      <div class="flex gap-2">
        <button
          type="button"
          @click="fillDemo('user')"
          class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-800 px-3 py-1.5 rounded"
        >
          Base User (dixon)
        </button>
        <button
          type="button"
          @click="fillDemo('admin')"
          class="text-xs bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded"
        >
          Admin User (admin)
        </button>
      </div>
    </div>
  </div>
</template>