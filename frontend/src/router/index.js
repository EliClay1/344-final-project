import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import JobDetailView from '../views/JobDetailView.vue'
import AdminView from '../views/AdminView.vue'
import { isAuthenticated, isAdmin } from '../services/authService'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { guestOnly: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true },
  },
  {
    path: '/jobs/:id',
    name: 'job-detail',
    component: JobDetailView,
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    return '/login'
  }
  if (to.meta.requiresAdmin && !isAdmin()) {
    return '/dashboard'
  }
  if (to.meta.guestOnly && isAuthenticated()) {
    return '/dashboard'
  }
})

export default router