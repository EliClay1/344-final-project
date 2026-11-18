<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import JobTable from '../components/JobTable.vue'
import { getJobs, getSystemLogs } from '../services/jobService'
import { USE_MOCK } from '../services/apiClient'

const jobs = ref([])
const logs = ref([])
const logFilter = ref('ALL')
const loading = ref(true)
const error = ref('')
let pollInterval = null

const filteredLogs = computed(() => logFilter.value === 'ALL'
  ? logs.value
  : logs.value.filter((log) => log.level === logFilter.value))

const stats = computed(() => ({
  total: jobs.value.length,
  active: jobs.value.filter((j) => j.status === 'queued' || j.status === 'running').length,
  completed: jobs.value.filter((j) => j.status === 'completed').length,
  failed: jobs.value.filter((j) => j.status === 'failed').length,
}))

async function loadAdminData(silent = false) {
  if (!silent) loading.value = true
  error.value = ''
  try {
    const [jobsData, logsData] = await Promise.all([getJobs(), getSystemLogs()])
    jobs.value = jobsData
    logs.value = logsData
  } catch (err) {
    error.value = err.message || 'Unable to load admin data.'
  } finally {
    if (!silent) loading.value = false
  }
}

onMounted(async () => {
  await loadAdminData()
  pollInterval = setInterval(() => loadAdminData(true), 4000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="page-stack">
    <div class="page-heading page-heading--action">
      <h1>Team activity</h1>
      <button class="secondary-button" type="button" @click="loadAdminData()">Refresh</button>
    </div>

    <p v-if="error" class="alert alert--error" role="alert">{{ error }}</p>

    <div class="summary-line" aria-label="Task summary">
      <div><strong>{{ stats.total }}</strong><span>Recent tasks</span></div>
      <div><strong>{{ stats.active }}</strong><span>Queued or running</span></div>
      <div><strong>{{ stats.completed }}</strong><span>Completed</span></div>
      <div><strong>{{ stats.failed }}</strong><span>Failed</span></div>
    </div>

    <section class="work-section" aria-labelledby="admin-history-title">
      <div class="panel-heading"><h2 id="admin-history-title">Recent tasks</h2></div>
      <p v-if="loading" class="panel-state">Loading tasks…</p>
      <JobTable v-else :jobs="jobs" :show-user="true" />
    </section>

    <section v-if="USE_MOCK" class="work-section" aria-labelledby="demo-activity-title">
      <div class="panel-heading panel-heading--wrap">
        <h2 id="demo-activity-title">Demo activity</h2>
        <div class="filter-group" aria-label="Filter events by level">
          <button v-for="level in ['ALL', 'INFO', 'ERROR']" :key="level" type="button" :class="{ active: logFilter === level }" @click="logFilter = level">{{ level === 'ALL' ? 'All' : level }}</button>
        </div>
      </div>
      <div class="activity-list">
        <div v-for="log in filteredLogs" :key="log.id" class="activity-row">
          <time :datetime="log.timestamp">{{ new Date(log.timestamp).toLocaleTimeString() }}</time>
          <span class="activity-level" :class="`activity-level--${log.level.toLowerCase()}`">{{ log.level }}</span>
          <span class="activity-source">{{ log.source }}</span>
          <span>{{ log.message }}</span>
        </div>
        <p v-if="filteredLogs.length === 0" class="panel-state">No events match this filter.</p>
      </div>
    </section>
  </div>
</template>
