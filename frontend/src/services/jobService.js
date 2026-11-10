
let jobs = [
  {
    id: 'job-001',
    url: 'https://example.com',
    task_type: 'screenshot',
    status: 'completed',
    active_agent: null,
    created_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    result: {
      message: 'Screenshot captured successfully',
      screenshot_url: null,
    },
  },
  {
    id: 'job-002',
    url: 'https://github.com',
    task_type: 'availability',
    status: 'running',
    active_agent: 'worker-01',
    created_at: new Date().toISOString(),
    completed_at: null,
    result: null,
  },
]

// Simulate network latency
const delay = (ms) =>
  new Promise((resolve) => setTimeout(resolve, ms))

// Get all jobs
export async function getJobs() {
  await delay(300)
  return structuredClone(jobs)
}

// Get a specific job
export async function getJob(id) {
  await delay(200)

  const job = jobs.find((job) => job.id === id)

  return job ? structuredClone(job) : null
}

// Submit a new job
export async function submitJob(url, taskType) {
  await delay(500)

  const job = {
    id: `job-${crypto.randomUUID()}`,
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
