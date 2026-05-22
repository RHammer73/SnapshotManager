<template>
  <div class="p-6 max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-white">Dashboard</h1>
      <p class="text-sm text-gray-400 mt-1">Übersicht aller Backup-Aktivitäten</p>
    </div>

    <!-- Aktiver Job -->
    <div v-if="activeJob" class="card border-brand-700">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <span class="relative flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
          </span>
          <h2 class="font-semibold text-white">Backup läuft</h2>
          <span class="badge-blue">{{ hostName(activeJob.host_id) }}</span>
        </div>
        <button @click="cancelJob" class="btn-danger text-xs py-1 px-3">Abbrechen</button>
      </div>

      <!-- Fortschrittsbalken Gesamt -->
      <ProgressBar
        :value="progress.overall_progress"
        label="Gesamt"
        color="brand"
        class="mb-3"
      />

      <!-- Fortschrittsbalken VM -->
      <ProgressBar
        v-if="progress.current_vm"
        :value="progress.vm_progress"
        :label="`VM ${progress.vm_index}/${progress.vm_total}: ${progress.current_vm}`"
        color="sky"
        class="mb-4"
      />

      <!-- Aktueller Schritt -->
      <p class="text-sm text-gray-300 mb-3">
        <span class="text-gray-500">Status:</span> {{ progress.step || 'Initialisiere...' }}
      </p>

      <!-- Live Log -->
      <LogViewer :logs="liveLog" :max-lines="15" />
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Hosts" :value="hosts.length" icon="server" color="brand" />
      <StatCard label="VMs (aktiv)" :value="enabledVmCount" icon="cube" color="sky" />
      <StatCard label="Jobs heute" :value="jobsToday" icon="clock" color="violet" />
      <StatCard label="Fehler (7 Tage)" :value="recentErrors" icon="exclamation" color="red" />
    </div>

    <!-- Letzte Jobs -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-semibold text-white">Letzte Jobs</h2>
        <RouterLink to="/jobs" class="text-xs text-brand-400 hover:text-brand-300">Alle anzeigen →</RouterLink>
      </div>
      <div v-if="recentJobs.length === 0" class="text-center py-8 text-gray-500 text-sm">
        Noch keine Jobs vorhanden
      </div>
      <div v-else class="space-y-2">
        <JobCard
          v-for="job in recentJobs"
          :key="job.id"
          :job="job"
          :host-name="hostName(job.host_id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useHostsStore } from '@/stores/hosts.js'
import { useJobsStore } from '@/stores/jobs.js'
import ProgressBar from '@/components/ProgressBar.vue'
import LogViewer from '@/components/LogViewer.vue'
import JobCard from '@/components/JobCard.vue'
import StatCard from '@/components/StatCard.vue'
import api from '@/api.js'

const hostsStore = useHostsStore()
const jobsStore = useJobsStore()

const hosts = computed(() => hostsStore.hosts)
const progress = ref({ overall_progress: 0, vm_progress: 0 })
const liveLog = ref([])
let sseSource = null
let refreshInterval = null

const activeJob = computed(() => jobsStore.jobs.find(j => ['running', 'pending'].includes(j.status)))
const recentJobs = computed(() => jobsStore.jobs.slice(0, 8))

const enabledVmCount = ref(0)
const jobsToday = computed(() => {
  const today = new Date().toDateString()
  return jobsStore.jobs.filter(j => new Date(j.started_at).toDateString() === today).length
})
const recentErrors = computed(() => {
  const cutoff = Date.now() - 7 * 86400 * 1000
  return jobsStore.jobs.filter(j => j.status === 'failed' && new Date(j.started_at) > cutoff).length
})

function hostName(hostId) {
  return hosts.value.find(h => h.id === hostId)?.name || `Host #${hostId}`
}

async function cancelJob() {
  if (activeJob.value) await jobsStore.cancelJob(activeJob.value.id)
}

function connectSSE(jobId) {
  if (sseSource) sseSource.close()
  sseSource = new EventSource(`/api/jobs/${jobId}/stream`)
  sseSource.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.ping) return
    progress.value = { ...progress.value, ...data }
    if (data.log) {
      liveLog.value.push({ level: data.level || 'info', message: data.log, ts: new Date() })
      if (liveLog.value.length > 100) liveLog.value.shift()
    }
    if (data.done) {
      sseSource.close()
      jobsStore.fetchJobs()
    }
  }
}

async function refresh() {
  await Promise.all([hostsStore.fetchHosts(), jobsStore.fetchJobs()])
  if (activeJob.value && (!sseSource || sseSource.readyState === EventSource.CLOSED)) {
    connectSSE(activeJob.value.id)
  }

  // Enabled-VM-Count ermitteln
  let count = 0
  for (const h of hosts.value) {
    try {
      const { data } = await api.get('/vms', { params: { host_id: h.id } })
      count += data.filter(v => v.enabled).length
    } catch {}
  }
  enabledVmCount.value = count
}

onMounted(() => {
  refresh()
  refreshInterval = setInterval(() => jobsStore.fetchJobs(), 10000)
})

onUnmounted(() => {
  clearInterval(refreshInterval)
  if (sseSource) sseSource.close()
})
</script>
