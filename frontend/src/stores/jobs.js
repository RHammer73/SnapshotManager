import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api.js'

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref([])
  const loading = ref(false)
  const activeJobId = ref(null)

  async function fetchJobs(hostId = null) {
    loading.value = true
    try {
      const params = hostId ? { host_id: hostId } : {}
      const { data } = await api.get('/jobs', { params })
      jobs.value = data
      const running = data.find(j => j.status === 'running' || j.status === 'pending')
      activeJobId.value = running ? running.id : null
    } finally {
      loading.value = false
    }
  }

  async function startJob(hostId, shutdownAfter = false) {
    const { data } = await api.post('/jobs', { host_id: hostId, shutdown_after: shutdownAfter })
    jobs.value.unshift(data)
    activeJobId.value = data.id
    return data
  }

  async function cancelJob(jobId) {
    const { data } = await api.post(`/jobs/${jobId}/cancel`)
    const idx = jobs.value.findIndex(j => j.id === jobId)
    if (idx !== -1) jobs.value[idx].status = 'cancelled'
    return data
  }

  async function getJobLogs(jobId) {
    const { data } = await api.get(`/jobs/${jobId}/logs`)
    return data
  }

  async function checkRunningStatus() {
    const { data } = await api.get('/jobs/status/running')
    return data.running
  }

  return { jobs, loading, activeJobId, fetchJobs, startJob, cancelJob, getJobLogs, checkRunningStatus }
})
