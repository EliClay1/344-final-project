<script setup>
import { ref } from 'vue'
import { submitJob } from '../services/jobService'

const emit = defineEmits(['job-submitted'])

const ALLOWED_TASKS = ['screenshot', 'availability_check']

const url = ref('')
const taskType = ref('screenshot')
const loading = ref(false)
const error = ref('')

function isPrivateOrLocalHost(hostname) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, '')
  if (
    host === 'localhost' ||
    host === '::1' ||
    host === '0.0.0.0' ||
    host.endsWith('.local') ||
    host.endsWith('.internal')
  ) {
    return true
  }

  const ipv4Match = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
  if (!ipv4Match) return false

  const octets = ipv4Match.slice(1).map(Number)
  if (octets.some((n) => n < 0 || n > 255)) return true

  const [a, b] = octets
  return (
    a === 127 ||
    a === 10 ||
    a === 0 ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 169 && b === 254)
  )
}

async function handleSubmit() {
  error.value = ''

  const rawUrl = url.value.trim()
  if (rawUrl.length > 2048) {
    error.value = 'URL must be 2,048 characters or fewer.'
    return
  }

  if (!ALLOWED_TASKS.includes(taskType.value)) {
    error.value = 'Invalid task type selected.'
    return
  }

  let parsedUrl
  try {
    parsedUrl = new URL(rawUrl)

    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      error.value = 'Only HTTP and HTTPS URLs are allowed.'
      return
    }
    if (parsedUrl.username || parsedUrl.password) {
      error.value = 'URLs with embedded credentials are not allowed.'
      return
    }
    if (isPrivateOrLocalHost(parsedUrl.hostname)) {
      error.value = 'Local or private network addresses are not allowed.'
      return
    }
  } catch {
    error.value = 'Please enter a valid public HTTP or HTTPS URL.'
    return
  }

  loading.value = true

  try {
    const job = await submitJob(parsedUrl.href, taskType.value)
    emit('job-submitted', job)
    url.value = ''
  } catch (err) {
    error.value = err.message || 'Failed to submit job.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="task-composer" aria-labelledby="new-task-title">
    <div class="panel-heading">
      <div><h2 id="new-task-title">Run a task</h2><p>Enter a public website to check.</p></div>
    </div>
    <form class="submit-form" @submit.prevent="handleSubmit">
      <div class="form-field form-field--url">
        <label for="job-url">Website URL</label>
        <input id="job-url" v-model="url" type="url" maxlength="2048" placeholder="https://example.com" required />
      </div>
      <div class="form-field form-field--type">
        <label for="task-type">Task type</label>
        <select id="task-type" v-model="taskType">
          <option value="screenshot">Screenshot</option>
          <option value="availability_check">Availability check</option>
        </select>
      </div>
      <button class="primary-button" type="submit" :disabled="loading">{{ loading ? 'Submitting…' : 'Run task' }}</button>
    </form>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  </section>
</template>
