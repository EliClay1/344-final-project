<script setup>
import { useRouter } from 'vue-router'

defineProps({
  jobs: {
    type: Array,
    required: true,
  },
  showUser: {
    type: Boolean,
    default: false,
  },
})

const router = useRouter()

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
            <th v-if="showUser" class="py-3 pr-4">User / ID</th>
            <th class="py-3 pr-4">URL</th>
            <th class="py-3 pr-4">Task</th>
            <th class="py-3 pr-4">Status</th>
            <th class="py-3 pr-4">Created</th>
            <th class="py-3 text-right">Details</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="job in jobs"
            :key="job.id"
            @click="router.push(`/jobs/${job.id}`)"
            class="border-b hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <td class="py-3 pr-4 text-sm font-mono text-blue-600">
              {{ job.id }}
            </td>

            <td v-if="showUser" class="py-3 pr-4 text-sm font-medium text-gray-700">
              {{ job.username || job.user_id || 'Unknown' }}
            </td>

            <td class="py-3 pr-4 break-all">
              {{ job.url }}
            </td>

            <td class="py-3 pr-4 capitalize">
              {{ job.task_type === 'availability_check' ? 'Availability Check' : 'Screenshot' }}
            </td>

            <td class="py-3 pr-4">
              <span
                class="px-3 py-1 rounded-full text-sm capitalize"
                :class="statusClass(job.status)"
              >
                {{ job.status }}
              </span>
            </td>

            <td class="py-3 pr-4 text-sm text-gray-600">
              {{ new Date(job.created_at).toLocaleString() }}
            </td>

            <td class="py-3 text-right text-sm font-medium text-blue-600">
              View &rarr;
            </td>
          </tr> 

          <tr v-if="jobs.length === 0">
            <td
              :colspan="showUser ? 7 : 6"
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
