
<script setup>
import { ref, onMounted } from 'vue'

import JobSubmission from './components/JobSubmission.vue'
import JobTable from './components/JobTable.vue'
import { getJobs } from './services/jobService'

const jobs = ref([])
const loading = ref(true)
const error = ref('')

async function loadJobs() {
  loading.value = true
  error.value = ''

  try {
    jobs.value = await getJobs()
  } catch {
    error.value = 'Unable to load jobs.'
  } finally {
    loading.value = false
  }
}

function handleJobSubmitted(job) {
  jobs.value.unshift(job)
}

onMounted(loadJobs)
</script>

<template>
  <div class="min-h-screen bg-gray-100 text-gray-900">
    <header class="bg-slate-900 text-white p-5">
      <h1 class="text-2xl font-bold">
        CYBER 344 Browser Farm
      </h1>

      <p class="text-sm text-gray-300">
        Kubernetes Browser Automation Dashboard
      </p>
    </header>

    <main class="max-w-5xl mx-auto p-6 space-y-6">
      <JobSubmission
        @job-submitted="handleJobSubmitted"
      />

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
      />
    </main>
  </div>
</template>
