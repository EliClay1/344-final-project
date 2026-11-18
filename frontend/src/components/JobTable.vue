<script setup>
defineProps({
  jobs: { type: Array, required: true },
  showUser: { type: Boolean, default: false },
})
</script>

<template>
  <p class="table-hint">Swipe sideways to see all columns.</p>
  <div class="table-scroll">
    <table class="task-table">
      <thead>
        <tr>
          <th scope="col">Website</th>
          <th v-if="showUser" scope="col">User</th>
          <th scope="col">Task</th>
          <th scope="col">Status</th>
          <th scope="col">Submitted</th>
          <th scope="col" aria-label="Task details"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobs" :key="job.id">
          <td class="task-table__website">
            <RouterLink :to="`/jobs/${job.id}`">{{ job.url }}</RouterLink>
            <small :title="job.id">{{ job.id.slice(0, 12) }}</small>
          </td>
          <td v-if="showUser" class="task-table__user" data-label="User">{{ job.username || job.user_id || 'Unknown' }}</td>
          <td data-label="Task">{{ job.task_type === 'availability_check' ? 'Availability check' : 'Screenshot' }}</td>
          <td data-label="Status"><span class="task-status" :class="`task-status--${job.status}`"><span aria-hidden="true"></span>{{ job.status }}</span></td>
          <td class="task-table__date" data-label="Submitted"><time :datetime="job.created_at">{{ new Date(job.created_at).toLocaleString() }}</time></td>
          <td class="task-table__link"><RouterLink :to="`/jobs/${job.id}`" :aria-label="`View task ${job.id}`">View task →</RouterLink></td>
        </tr>
        <tr v-if="jobs.length === 0"><td :colspan="showUser ? 6 : 5" class="empty-row">No tasks have been submitted yet.</td></tr>
      </tbody>
    </table>
  </div>
</template>
