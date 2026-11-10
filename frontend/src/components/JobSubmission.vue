
<script setup>
import { ref } from 'vue'
import { submitJob } from '../services/jobService'

const emit = defineEmits(['job-submitted'])

const url = ref('')
const taskType = ref('screenshot')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''

  let parsedUrl

  try {
    parsedUrl = new URL(url.value.trim())

    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      throw new Error('Invalid protocol')
    }
  } catch {
    error.value = 'Please enter a valid HTTP or HTTPS URL.'
    return
  }

  loading.value = true

  try {
    const job = await submitJob(
      parsedUrl.href,
      taskType.value
    )

    emit('job-submitted', job)
    url.value = ''
  } catch {
    error.value = 'Failed to submit job.'
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

          <option value="availability">
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
