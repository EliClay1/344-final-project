<script setup>
import { useRouter } from 'vue-router'
import { currentUser, isAdmin, logout } from './services/authService'
import { USE_MOCK } from './services/apiClient'

const router = useRouter()

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-header__inner content-width">
        <RouterLink class="app-name" to="/dashboard">
          <svg class="app-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="2" y="3" width="20" height="18" rx="2" stroke="currentColor" stroke-width="1.7" />
            <path d="M2 8h20M5 5.5h.01M8 5.5h.01" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            <path d="m8 15 2.5 2.5L16 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>Browser Farm</span>
        </RouterLink>
        <span class="course-label">CYBER 344</span>
        <nav v-if="currentUser" class="app-nav" aria-label="Main navigation">
          <RouterLink to="/dashboard" active-class="active">Dashboard</RouterLink>
          <RouterLink v-if="isAdmin()" to="/admin" active-class="active">Admin</RouterLink>
        </nav>
        <div v-if="currentUser" class="account-menu">
          <span class="mode-label" :class="{ 'mode-label--demo': USE_MOCK }">{{ USE_MOCK ? 'Demo' : 'Live' }}</span>
          <span>{{ currentUser.username }} <span class="account-role">({{ isAdmin() ? 'admin' : 'user' }})</span></span>
          <button type="button" @click="handleLogout">Sign out</button>
        </div>
        <span v-else class="mode-label">{{ USE_MOCK ? 'Demo mode' : 'Live API' }}</span>
      </div>
    </header>

    <main class="content-width app-main"><RouterView /></main>
  </div>
</template>
