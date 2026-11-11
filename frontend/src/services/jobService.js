import { currentUser, isAdmin } from './authService'
import { apiRequest, USE_MOCK } from './apiClient'

let jobs = [
  {
    id: 'job-001',
    user_id: 2,
    username: 'dixon',
    url: 'https://example.com',
    task_type: 'screenshot',
    status: 'completed',
    active_agent: null,
    created_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    result: {
      message: 'Screenshot captured successfully',
      screenshot_url: 'https://placehold.co',
    },
  },
  {
    id: 'job-002',
    user_id: 3,
    username: 'andrew',
    url: 'https://github.com',
    task_type: 'availability',
    status: 'running',
    active_agent: 'worker-01',
    created_at: new Date().toISOString(),
    completed_at: null,
    result: null,
  },
]

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function simulateWorkerProgress() {
  jobs = jobs.map((job) => {
    if (job.status === 'queued') {
      return {
        ...job,
        status: 'running',
        active_agent: `k8s-worker-${Math.floor(10 + Math.random() * 90)}`,
      }
    }

    if (job.status === 'running') {
      const shouldFail = job.url.toLowerCase().includes('fail')

      return {
        ...job,
        status: shouldFail ? 'failed' : 'completed',
        active_agent: null,
        completed_at: new Date().toISOString(),
        result: shouldFail
          ? {
              message: 'Connection timed out: target host did not respond within 10s.',
              screenshot_url: null,
            }
          : {
              message:
                job.task_type === 'screenshot'
                  ? 'Screenshot captured successfully'
                  : 'Site is reachable (HTTP 200 OK)',
              screenshot_url:
                job.task_type === 'screenshot'
                  ? 'https://placehold.co'
                  : null,
            },
      }
    }

    return job
  })
}

export async function getJobs() {
  if (!USE_MOCK) {
    return await apiRequest('/jobs')
  }

  await delay(300)
  simulateWorkerProgress()

  if (!currentUser.value) {
    return []
  }

  if (isAdmin()) {
    return structuredClone(jobs)
  }

  const userJobs = jobs.filter(
    (job) => job.username.toLowerCase() === currentUser.value.username.toLowerCase()
  )
  return structuredClone(userJobs)
}

export async function getJob(id) {
  if (!USE_MOCK) {
    return await apiRequest(`/jobs/${encodeURIComponent(id)}`)
  }

  await delay(200)

  const job = jobs.find((job) => job.id === id)
  if (!job || !currentUser.value) {
    return null
  }

  const isOwner = job.username.toLowerCase() === currentUser.value.username.toLowerCase()
  if (!isAdmin() && !isOwner) {
    throw new Error('Unauthorized: You do not have permission to view this job.')
  }

  return structuredClone(job)
}

export async function submitJob(url, taskType) {
  if (!USE_MOCK) {
    return await apiRequest('/jobs', {
      method: 'POST',
      body: JSON.stringify({
        url,
        task_type: taskType,
      }),
    })
  }

  await delay(500)

  if (!currentUser.value) {
    throw new Error('You must be signed in to submit a job.')
  }

  const job = {
    id: `job-${crypto.randomUUID().slice(0, 8)}`,
    user_id: currentUser.value.id,
    username: currentUser.value.username,
    url,
    task_type: taskType,
    status: 'queued',
    active_agent: null,
    created_at: new Date().toISOString(),
    completed_at: null,
    result: null,
  }

  jobs.unshift(job)

  return structuredClone(job)
}

export async function getSystemLogs() {
  if (!USE_MOCK) {
    return await apiRequest('/admin/logs')
  }

  await delay(250)

  if (!isAdmin()) {
    throw new Error('Unauthorized: Admin access required to view system logs.')
  }

  const now = Date.now()

  const logs = [
    {
      id: 'log-101',
      timestamp: new Date(now - 120000).toISOString(),
      level: 'INFO',
      source: 'api-gateway',
      message: 'Input sanitization passed for incoming task request (URL validated).',
    },
    {
      id: 'log-102',
      timestamp: new Date(now - 95000).toISOString(),
      level: 'INFO',
      source: 'k8s-autoscaler',
      message: 'Queue depth threshold reached; scaling worker deployment from 1 to 3 pods.',
    },
    {
      id: 'log-103',
      timestamp: new Date(now - 60000).toISOString(),
      level: 'INFO',
      source: 'worker-01',
      message: 'Spawned isolated Docker sandbox container with restricted network/filesystem permissions.',
    },
    ...jobs.slice(0, 5).map((job) => ({
      id: `log-job-${job.id}`,
      timestamp: job.completed_at || job.created_at,
      level: job.status === 'failed' ? 'ERROR' : 'INFO',
      source: job.active_agent || 'k8s-worker-pool',
      message:
        job.status === 'failed'
          ? `[${job.id}] Worker container exited with error for ${job.url}: ${job.result?.message || 'Task failed'}`
          : `[${job.id}] User "${job.username}" (${job.task_type}) -> status: ${job.status.toUpperCase()}`,
    })),
  ]

  return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
}
