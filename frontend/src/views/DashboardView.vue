<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import JobSubmission from '../components/JobSubmission.vue'
import JobTable from '../components/JobTable.vue'
import { getJobs } from '../services/jobService'
import { isAdmin } from '../services/authService'

const jobs = ref([])
const loading = ref(true)
const error = ref('')
let pollInterval = null

const hasActiveJobs = computed(() =>
  jobs.value.some((job) => job.status === 'queued' || job.status === 'running')
)

async function loadJobs(silent = false) {
  if (!silent) loading.value = true
  error.value = ''
  try {
    jobs.value = await getJobs()
  } catch (err) {
    error.value = err.message || 'Unable to load tasks.'
  } finally {
    if (!silent) loading.value = false
  }
}

function handleJobSubmitted(job) {
  jobs.value.unshift(job)
}

onMounted(async () => {
  await loadJobs()
  pollInterval = setInterval(() => {
    if (hasActiveJobs.value) loadJobs(true)
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="page-stack">
    <div class="page-heading">
      <h1>Tasks</h1>
    </div>

    <p v-if="error" class="alert alert--error" role="alert">{{ error }}</p>

    <JobSubmission @job-submitted="handleJobSubmitted" />

    <section class="work-section" aria-labelledby="history-title">
      <div class="panel-heading">
        <h2 id="history-title">Recent tasks</h2>
        <div class="history-meta">
          <span v-if="hasActiveJobs" class="refresh-note" aria-live="polite"><span class="refresh-dot"></span>Updating active tasks</span>
          <span v-else class="task-count">{{ jobs.length }} shown</span>
        </div>
      </div>
      <p v-if="loading" class="panel-state">Loading tasks…</p>
      <JobTable v-else :jobs="jobs" :show-user="isAdmin()" />
    </section>
  </div>
</template>
