<script setup>
import { useRouter } from 'vue-router'
import { currentUser, isAdmin, logout } from './services/authService'

const router = useRouter()

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-gray-100 text-gray-900">
    <header class="bg-slate-900 text-white p-5">
      <div class="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-8">
          <div>
            <h1 class="text-2xl font-bold">
              CYBER 344 Browser Farm
            </h1>
            <p class="text-sm text-gray-300">
              Kubernetes Browser Automation Dashboard
            </p>
          </div>

          <nav
            v-if="currentUser"
            class="flex items-center gap-4 text-sm font-medium"
          >
            <RouterLink
              to="/dashboard"
              class="text-gray-300 hover:text-white transition-colors"
              active-class="text-white underline underline-offset-4"
            >
              Dashboard
            </RouterLink>

            <RouterLink
              v-if="isAdmin()"
              to="/admin"
              class="text-gray-300 hover:text-white transition-colors"
              active-class="text-white underline underline-offset-4"
            >
              Admin Panel
            </RouterLink>
          </nav>
        </div>

        <div
          v-if="currentUser"
          class="flex items-center gap-4"
        >
          <span class="text-sm text-gray-300">
            Signed in as <strong class="text-white">{{ currentUser.username }}</strong>
            <span class="ml-1.5 px-2 py-0.5 text-xs rounded bg-slate-700 uppercase">
              {{ isAdmin() ? 'Admin' : 'User' }}
            </span>
          </span>

          <button
            type="button"
            @click="handleLogout"
            class="bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-1.5 rounded"
          >
            Logout
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-5xl mx-auto p-6">
      <RouterView />
    </main>
  </div>
</template>
