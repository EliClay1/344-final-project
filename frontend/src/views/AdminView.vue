<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import JobTable from '../components/JobTable.vue'
import { getJobs, getSystemLogs } from '../services/jobService'

const jobs = ref([])
const logs = ref([])
const logFilter = ref('ALL')
const loading = ref(true)
const error = ref('')
let pollInterval = null

const filteredLogs = computed(() => {
  if (logFilter.value === 'ALL') {
    return logs.value
  }
  return logs.value.filter((log) => log.level === logFilter.value)
})

const stats = computed(() => ({
  total: jobs.value.length,
  active: jobs.value.filter((j) => j.status === 'queued' || j.status === 'running').length,
  completed: jobs.value.filter((j) => j.status === 'completed').length,
  failed: jobs.value.filter((j) => j.status === 'failed').length,
}))

function levelBadge(level) {
  if (level === 'ERROR') return 'text-red-400'
  if (level === 'WARN') return 'text-yellow-400'
  return 'text-emerald-400'
}

async function loadAdminData(silent = false) {
  if (!silent) {
    loading.value = true
  }
  error.value = ''

  try {
    const [jobsData, logsData] = await Promise.all([
      getJobs(),
      getSystemLogs(),
    ])
    jobs.value = jobsData
    logs.value = logsData
  } catch (err) {
    error.value = err.message || 'Unable to load admin data.'
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

onMounted(async () => {
  await loadAdminData()

  pollInterval = setInterval(() => {
    loadAdminData(true)
  }, 4000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold">
          Admin Control &amp; Logs
        </h2>
        <p class="text-sm text-gray-600">
          Global task monitor across all users and Kubernetes worker telemetry.
        </p>
      </div>

      <button
        type="button"
        @click="loadAdminData()"
        class="bg-slate-800 hover:bg-slate-700 text-white text-sm px-4 py-2 rounded"
      >
        Refresh Data
      </button>
    </div>

    <div
      v-if="error"
      class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg"
      role="alert"
    >
      {{ error }}
    </div>

    <!-- Cluster / Job Summary Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-white shadow rounded-lg p-4">
        <p class="text-xs uppercase text-gray-500">Total Jobs</p>
        <p class="text-2xl font-bold mt-1">{{ stats.total }}</p>
      </div>
      <div class="bg-white shadow rounded-lg p-4">
        <p class="text-xs uppercase text-gray-500">Active Containers</p>
        <p class="text-2xl font-bold text-yellow-600 mt-1">{{ stats.active }}</p>
      </div>
      <div class="bg-white shadow rounded-lg p-4">
        <p class="text-xs uppercase text-gray-500">Completed</p>
        <p class="text-2xl font-bold text-green-600 mt-1">{{ stats.completed }}</p>
      </div>
      <div class="bg-white shadow rounded-lg p-4">
        <p class="text-xs uppercase text-gray-500">Failed</p>
        <p class="text-2xl font-bold text-red-600 mt-1">{{ stats.failed }}</p>
      </div>
    </div>

    <!-- System & Kubernetes Logs Terminal -->
    <section class="bg-slate-900 text-gray-100 shadow rounded-lg p-6">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h3 class="text-lg font-semibold text-white">
            Application &amp; Kubernetes Logs
          </h3>
          <p class="text-xs text-gray-400">
            Live output from API sanitization layer, K8s autoscaler, and worker containers
          </p>
        </div>

        <div class="flex items-center gap-2 text-xs">
          <button
            v-for="level in ['ALL', 'INFO', 'ERROR']"
            :key="level"
            type="button"
            @click="logFilter = level"
            class="px-3 py-1 rounded font-medium transition-colors"
            :class="logFilter === level ? 'bg-blue-600 text-white' : 'bg-slate-800 text-gray-300 hover:bg-slate-700'"
          >
            {{ level }}
          </button>
        </div>
      </div>

      <div class="bg-slate-950 rounded p-4 font-mono text-xs space-y-2 max-h-72 overflow-y-auto border border-slate-800">
        <div
          v-for="log in filteredLogs"
          :key="log.id"
          class="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3 border-b border-slate-900 pb-1.5"
        >
          <span class="text-gray-500 shrink-0">
            {{ new Date(log.timestamp).toLocaleTimeString() }}
          </span>
          <span
            class="font-bold shrink-0 w-12"
            :class="levelBadge(log.level)"
          >
            [{{ log.level }}]
          </span>
          <span class="text-sky-400 shrink-0">
            ({{ log.source }})
          </span>
          <span class="text-gray-200 break-all">
            {{ log.message }}
          </span>
        </div>

        <p
          v-if="filteredLogs.length === 0"
          class="text-gray-500 italic"
        >
          No logs match the selected filter.
        </p>
      </div>
    </section>

    <!-- Global Job Table Across All Users -->
    <p
      v-if="loading"
      class="text-gray-500"
    >
      Loading global job history...
    </p>

    <JobTable
      v-else
      :jobs="jobs"
      :show-user="true"
    />
  </div>
</template>