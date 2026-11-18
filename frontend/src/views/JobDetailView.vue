<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { getJob, screenshotUrl } from '../services/jobService'

const route = useRoute()
const job = ref(null)
const loading = ref(true)
const error = ref('')
const screenshotFailed = ref(false)
let pollInterval = null

const safeScreenshotUrl = computed(() => screenshotUrl(job.value))
const hasObservations = computed(() => {
  const result = job.value?.result
  return Boolean(result && (result.page_title || result.http_status != null || result.load_time_ms != null || result.final_url))
})

async function fetchJob(silent = false) {
  if (!silent) loading.value = true
  error.value = ''
  try {
    const data = await getJob(route.params.id)
    if (!data) {
      error.value = 'Task not found.'
    } else {
      if (job.value?.status !== 'completed' && data.status === 'completed') screenshotFailed.value = false
      job.value = data
    }
  } catch (err) {
    error.value = err.message || 'Unable to load task details.'
  } finally {
    if (!silent) loading.value = false
  }
}

onMounted(async () => {
  await fetchJob()
  pollInterval = setInterval(() => {
    if (job.value && (job.value.status === 'queued' || job.value.status === 'running')) fetchJob(true)
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="page-stack">
    <RouterLink class="back-link" to="/dashboard">← Back to dashboard</RouterLink>
    <p v-if="loading" class="panel-state">Loading task details…</p>
    <p v-else-if="error" class="alert alert--error" role="alert">{{ error }}</p>

    <template v-else-if="job">
      <div class="page-heading detail-heading">
        <div><h1>Task details <span class="detail-reference">#{{ job.id.slice(0, 8) }}</span></h1><p class="detail-url">{{ job.url }}</p></div>
        <span class="task-status" :class="`task-status--${job.status}`"><span aria-hidden="true"></span>{{ job.status }}</span>
      </div>

      <section class="work-section" aria-label="Task information">
        <dl class="metadata-grid">
          <div><dt>Task ID</dt><dd class="mono-value">{{ job.id }}</dd></div>
          <div><dt>Type</dt><dd>{{ job.task_type === 'availability_check' ? 'Availability check' : 'Screenshot' }}</dd></div>
          <div><dt>Submitted</dt><dd>{{ new Date(job.created_at).toLocaleString() }}</dd></div>
          <div><dt>Completed</dt><dd>{{ job.completed_at ? new Date(job.completed_at).toLocaleString() : '—' }}</dd></div>
          <div v-if="job.active_agent"><dt>Worker</dt><dd>{{ job.active_agent }}</dd></div>
        </dl>
      </section>

      <section class="work-section result-section" aria-labelledby="result-title">
        <div class="panel-heading"><div><h2 id="result-title">Result</h2></div></div>
        <div v-if="job.status === 'queued' || job.status === 'running'" class="result-message result-message--pending" aria-live="polite">
          <strong>{{ job.status === 'queued' ? 'Waiting for a worker' : 'Task is running' }}</strong>
          <p>This page updates automatically when the task finishes.</p>
        </div>
        <div v-else-if="job.status === 'failed'" class="result-message result-message--failed" role="alert">
          <strong>Task failed</strong><p>{{ job.error || 'An unexpected error occurred while processing this URL.' }}</p>
        </div>
        <div v-else-if="job.status === 'completed'" class="result-message result-message--complete">
          <strong>{{ job.task_type === 'availability_check' ? (job.result?.is_up ? 'Website is reachable' : 'Website did not respond successfully') : 'Screenshot captured' }}</strong>
        </div>

        <dl v-if="job.status === 'completed' && hasObservations" class="result-details">
          <div v-if="job.result.page_title"><dt>Page title</dt><dd>{{ job.result.page_title }}</dd></div>
          <div v-if="job.result.http_status != null"><dt>HTTP status</dt><dd>{{ job.result.http_status }}</dd></div>
          <div v-if="job.result.load_time_ms != null"><dt>Load time</dt><dd>{{ job.result.load_time_ms }} ms</dd></div>
          <div v-if="job.result.final_url"><dt>Final URL</dt><dd class="break-value">{{ job.result.final_url }}</dd></div>
        </dl>
      </section>

      <section v-if="job.status === 'completed' && job.task_type === 'screenshot'" class="work-section screenshot-section" aria-labelledby="screenshot-title">
        <div class="panel-heading"><div><h2 id="screenshot-title">Screenshot</h2></div></div>
        <img v-if="safeScreenshotUrl && !screenshotFailed" :src="safeScreenshotUrl" :alt="`Screenshot of ${job.url}`" @error="screenshotFailed = true" />
        <p v-else class="panel-state">Screenshot is unavailable or has expired.</p>
      </section>
    </template>
  </div>
</template>
