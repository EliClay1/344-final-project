
<script setup>
defineProps({
  jobs: {
    type: Array,
    required: true,
  },
})

function statusClass(status) {
  const classes = {
    completed: 'bg-green-100 text-green-800',
    running: 'bg-yellow-100 text-yellow-800',
    queued: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  }

  return classes[status] ?? classes.queued
}
</script>

<template>
  <section class="bg-white shadow rounded-lg p-6">
    <h2 class="text-xl font-semibold mb-4">
      Job History
    </h2>

    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b">
            <th class="py-3 pr-4">Job ID</th>
            <th class="py-3 pr-4">URL</th>
            <th class="py-3 pr-4">Task</th>
            <th class="py-3 pr-4">Status</th>
            <th class="py-3">Created</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="job in jobs"
            :key="job.id"
            class="border-b"
          >
            <td class="py-3 pr-4 text-sm">
              {{ job.id }}
            </td>

            <td class="py-3 pr-4 break-all">
              {{ job.url }}
            </td>

            <td class="py-3 pr-4 capitalize">
              {{ job.task_type }}
            </td>

            <td class="py-3 pr-4">
              <span
                class="px-3 py-1 rounded-full text-sm capitalize"
                :class="statusClass(job.status)"
              >
                {{ job.status }}
              </span>
            </td>

            <td class="py-3 text-sm text-gray-600">
              {{ new Date(job.created_at).toLocaleString() }}
            </td>
          </tr>

          <tr v-if="jobs.length === 0">
            <td
              colspan="5"
              class="py-6 text-gray-500"
            >
              No jobs submitted yet.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
