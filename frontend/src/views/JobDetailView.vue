<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJob, screenshotUrl } from '../services/jobService'

const route = useRoute()
const router = useRouter()

const job = ref(null)
const loading = ref(true)
const error = ref('')
const screenshotFailed = ref(false)
let pollInterval = null

const safeScreenshotUrl = computed(() => screenshotUrl(job.value))

function statusClass(status) {
  const classes = {
    completed: 'bg-green-100 text-green-800',
    running: 'bg-yellow-100 text-yellow-800',
    queued: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  }

  return classes[status] ?? classes.queued
}

async function fetchJob(silent = false) {
  if (!silent) {
    loading.value = true
  }
  error.value = ''

  try {
    const data = await getJob(route.params.id)
    if (!data) {
      error.value = 'Job not found.'
    } else {
      if (job.value?.status !== 'completed' && data.status === 'completed') screenshotFailed.value = false
      job.value = data
    }
  } catch (err) {
    error.value = err.message || 'Unable to load job details.'
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

onMounted(async () => {
  await fetchJob()

  pollInterval = setInterval(() => {
    if (job.value && (job.value.status === 'queued' || job.value.status === 'running')) {
      fetchJob(true)
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
    <div>
      <button
        type="button"
        @click="router.push('/dashboard')"
        class="text-sm text-blue-600 hover:text-blue-800 font-medium"
      >
        &larr; Back to Dashboard
      </button>
    </div>

    <p
      v-if="loading"
      class="text-gray-500"
    >
      Loading job details...
    </p>

    <div
      v-else-if="error"
      class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg"
      role="alert"
    >
      {{ error }}
    </div>

    <section
      v-else-if="job"
      class="bg-white shadow rounded-lg p-6 space-y-6"
    >
      <div class="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
        <div>
          <p class="text-xs uppercase tracking-wide text-gray-500">
            Job ID: {{ job.id }}
          </p>
          <h2 class="text-xl font-semibold break-all mt-1">
            {{ job.url }}
          </h2>
        </div>

        <span
          class="px-3 py-1 rounded-full text-sm font-medium capitalize"
          :class="statusClass(job.status)"
        >
          {{ job.status }}
        </span>
      </div>

      <dl class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <div class="bg-gray-50 p-3 rounded">
          <dt class="text-gray-500">Task Type</dt>
          <dd class="font-medium mt-1">{{ job.task_type === 'availability_check' ? 'Availability Check' : 'Screenshot' }}</dd>
        </div>

        <div class="bg-gray-50 p-3 rounded">
          <dt class="text-gray-500">Submitted</dt>
          <dd class="font-medium mt-1">{{ new Date(job.created_at).toLocaleString() }}</dd>
        </div>

        <div class="bg-gray-50 p-3 rounded">
          <dt class="text-gray-500">Completed</dt>
          <dd class="font-medium mt-1">
            {{ job.completed_at ? new Date(job.completed_at).toLocaleString() : 'In progress...' }}
          </dd>
        </div>
      </dl>

      <!-- Active State -->
      <div
        v-if="job.status === 'queued' || job.status === 'running'"
        class="bg-blue-50 border border-blue-200 text-blue-800 p-4 rounded-lg text-sm"
      >
        This task is currently <strong>{{ job.status }}</strong>. Results will appear automatically once finished.
      </div>

      <!-- Failed State -->
      <div
        v-else-if="job.status === 'failed'"
        class="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg"
        role="alert"
      >
        <h3 class="font-semibold mb-1">Task Failed</h3>
        <p class="text-sm">
          {{ job.error || 'An unexpected error occurred while processing this URL.' }}
        </p>
      </div>

      <!-- Completed State -->
      <div
        v-else-if="job.status === 'completed'"
        class="space-y-4"
      >
        <div class="bg-green-50 border border-green-200 text-green-800 p-4 rounded-lg">
          <h3 class="font-semibold mb-1">Result Summary</h3>
          <p class="text-sm">
            {{ job.task_type === 'availability_check'
              ? (job.result?.is_up ? 'Website is reachable.' : 'Website did not return a successful response.')
              : 'Screenshot captured successfully.' }}
          </p>
        </div>

        <dl v-if="job.result" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div v-if="job.result.page_title" class="bg-gray-50 p-3 rounded">
            <dt class="text-gray-500">Page title</dt>
            <dd class="font-medium break-all">{{ job.result.page_title }}</dd>
          </div>
          <div v-if="job.result.http_status != null" class="bg-gray-50 p-3 rounded">
            <dt class="text-gray-500">HTTP status</dt>
            <dd class="font-medium">{{ job.result.http_status }}</dd>
          </div>
          <div v-if="job.result.load_time_ms != null" class="bg-gray-50 p-3 rounded">
            <dt class="text-gray-500">Load time</dt>
            <dd class="font-medium">{{ job.result.load_time_ms }} ms</dd>
          </div>
          <div v-if="job.result.final_url" class="bg-gray-50 p-3 rounded">
            <dt class="text-gray-500">Final URL</dt>
            <dd class="font-medium break-all">{{ job.result.final_url }}</dd>
          </div>
        </dl>

        <div v-if="job.task_type === 'screenshot'">
          <h3 class="font-medium mb-2">Captured Screenshot</h3>
          <div
            v-if="safeScreenshotUrl && !screenshotFailed"
            class="border border-gray-200 rounded-lg overflow-hidden bg-gray-100"
          >
            <img
              :src="safeScreenshotUrl"
              :alt="`Screenshot of ${job.url}`"
              class="w-full h-auto"
              @error="screenshotFailed = true"
            />
          </div>
          <p
            v-else
            class="text-sm text-gray-500 italic"
          >
            Screenshot is unavailable or has expired.
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
