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
  <section class="bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-4">
      Submit a Job
    </h2>

    <form
      @submit.prevent="handleSubmit"
      class="space-y-4"
    >
      <div>
        <label
          for="job-url"
          class="block mb-2 font-medium"
        >
          Website URL
        </label>

        <input
          id="job-url"
          v-model="url"
          type="url"
          maxlength="2048"
          placeholder="https://example.com"
          required
          class="w-full border border-gray-300 rounded px-4 py-2"
        />
      </div>

      <div>
        <label
          for="task-type"
          class="block mb-2 font-medium"
        >
          Task Type
        </label>

        <select
          id="task-type"
          v-model="taskType"
          class="w-full border border-gray-300 rounded px-4 py-2"
        >
          <option value="screenshot">
            Screenshot
          </option>

          <option value="availability_check">
            Availability Check
          </option>
        </select>
      </div>

      <p
        v-if="error"
        class="text-red-600 text-sm"
        role="alert"
      >
        {{ error }}
      </p>

      <button
        type="submit"
        :disabled="loading"
        class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded"
      >
        {{ loading ? 'Submitting...' : 'Submit Job' }}
      </button>
    </form>
  </section>
</template>
