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

// Only poll if at least one job is still queued or running
const hasActiveJobs = computed(() =>
  jobs.value.some((job) => job.status === 'queued' || job.status === 'running')
)

async function loadJobs(silent = false) {
  if (!silent) {
    loading.value = true
  }
  error.value = ''

  try {
    jobs.value = await getJobs()
  } catch {
    error.value = 'Unable to load jobs.'
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

function handleJobSubmitted(job) {
  jobs.value.unshift(job)
}

onMounted(async () => {
  await loadJobs()

  pollInterval = setInterval(() => {
    if (hasActiveJobs.value) {
      loadJobs(true)
    }
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="space-y-6">
    <JobSubmission @job-submitted="handleJobSubmitted" />

    <div
      v-if="hasActiveJobs"
      class="flex items-center gap-2 text-sm text-blue-700 bg-blue-50 border border-blue-200 px-4 py-2 rounded-lg"
    >
      <span class="inline-block w-2 h-2 rounded-full bg-blue-600 animate-ping"></span>
      <span>Auto-refreshing active Kubernetes tasks...</span>
    </div>

    <p
      v-if="error"
      class="text-red-600"
      role="alert"
    >
      {{ error }}
    </p>

    <p
      v-if="loading"
      class="text-gray-500"
    >
      Loading jobs...
    </p>

    <JobTable
      v-else
      :jobs="jobs"
      :show-user="isAdmin()"
    />
  </div>
</template>