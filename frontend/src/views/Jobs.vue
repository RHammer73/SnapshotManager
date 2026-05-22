<template>
  <div class="p-6 max-w-5xl mx-auto space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Backup-Jobs</h1>
        <p class="text-sm text-gray-400 mt-1">Verlauf aller Backup-Vorgänge</p>
      </div>
      <div class="flex gap-2">
        <select v-model="filterHost" class="input w-44 text-sm">
          <option value="">Alle Hosts</option>
          <option v-for="h in hosts" :key="h.id" :value="h.id">{{ h.name }}</option>
        </select>
        <button @click="refresh" class="btn-secondary">
          <ArrowPathIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Aktiver Job mit Fortschritt -->
    <div v-if="activeJob" class="card border-brand-700">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <span class="relative flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
          </span>
          <h2 class="font-semibold text-white">Job #{{ activeJob.id }} läuft</h2>
        </div>
        <button @click="cancelActiveJob" class="btn-danger py-1 px-3 text-xs">Abbrechen</button>
      </div>
      <ProgressBar :value="progress.overall_progress" label="Gesamt" color="brand" class="mb-3" />
      <ProgressBar v-if="progress.current_vm" :value="progress.vm_progress" :label="`VM: ${progress.current_vm}`" color="sky" class="mb-4" />
      <p class="text-sm text-gray-400 mb-3">{{ progress.step }}</p>
      <LogViewer :logs="liveLog" :max-lines="12" />
    </div>

    <!-- Jobs-Liste -->
    <div class="space-y-2">
      <div v-if="filteredJobs.length === 0" class="card text-center py-12 text-gray-500">
        Keine Jobs gefunden
      </div>
      <div
        v-for="job in filteredJobs"
        :key="job.id"
        class="card hover:border-gray-700 transition-colors cursor-pointer"
        @click="selectedJob = selectedJob?.id === job.id ? null : job"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <StatusDot :status="job.status" />
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-white">Job #{{ job.id }}</span>
                <span class="badge-gray text-xs">{{ hostName(job.host_id) }}</span>
                <span class="badge-gray text-xs capitalize">{{ job.triggered_by }}</span>
              </div>
              <div class="text-xs text-gray-500 mt-0.5">
                {{ formatDate(job.started_at) }}
                <span v-if="job.finished_at"> · {{ duration(job.started_at, job.finished_at) }}</span>
                <span v-if="job.job_vms?.length"> · {{ job.job_vms.length }} VMs</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span :class="statusBadge(job.status)">{{ statusLabel(job.status) }}</span>
            <ChevronDownIcon class="w-4 h-4 text-gray-600" :class="selectedJob?.id === job.id ? 'rotate-180' : ''" />
          </div>
        </div>

        <!-- Expanded: Logs -->
        <div v-if="selectedJob?.id === job.id" class="mt-4 pt-4 border-t border-gray-800">
          <JobLogPanel :job-id="job.id" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ArrowPathIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'
import { useHostsStore } from '@/stores/hosts.js'
import { useJobsStore } from '@/stores/jobs.js'
import ProgressBar from '@/components/ProgressBar.vue'
import LogViewer from '@/components/LogViewer.vue'
import StatusDot from '@/components/StatusDot.vue'
import JobLogPanel from '@/components/JobLogPanel.vue'

const hostsStore = useHostsStore()
const jobsStore = useJobsStore()
const filterHost = ref('')
const selectedJob = ref(null)
const progress = ref({})
const liveLog = ref([])
let sseSource = null
let pollInterval = null

const hosts = computed(() => hostsStore.hosts)
const filteredJobs = computed(() => {
  if (!filterHost.value) return jobsStore.jobs
  return jobsStore.jobs.filter(j => j.host_id === parseInt(filterHost.value))
})
const activeJob = computed(() => jobsStore.jobs.find(j => ['running', 'pending'].includes(j.status)))

function hostName(id) { return hosts.value.find(h => h.id === id)?.name || `#${id}` }
function formatDate(d) { return d ? new Date(d).toLocaleString('de-DE') : '—' }
function duration(start, end) {
  const s = Math.floor((new Date(end) - new Date(start)) / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`
}
function statusLabel(s) { return { pending: 'Ausstehend', running: 'Läuft', completed: 'Abgeschlossen', failed: 'Fehler', cancelled: 'Abgebrochen' }[s] || s }
function statusBadge(s) { return { pending: 'badge-yellow', running: 'badge-blue', completed: 'badge-green', failed: 'badge-red', cancelled: 'badge-gray' }[s] || 'badge-gray' }

function connectSSE(jobId) {
  if (sseSource) sseSource.close()
  progress.value = {}
  liveLog.value = []
  sseSource = new EventSource(`/api/jobs/${jobId}/stream`)
  sseSource.onmessage = e => {
    const data = JSON.parse(e.data)
    if (data.ping) return
    progress.value = { ...progress.value, ...data }
    if (data.log) {
      liveLog.value.push({ level: data.level || 'info', message: data.log, ts: new Date() })
      if (liveLog.value.length > 100) liveLog.value.shift()
    }
    if (data.done) { sseSource.close(); jobsStore.fetchJobs() }
  }
}

async function cancelActiveJob() {
  if (activeJob.value) await jobsStore.cancelJob(activeJob.value.id)
}

async function refresh() {
  await Promise.all([hostsStore.fetchHosts(), jobsStore.fetchJobs()])
}

watch(activeJob, (job) => {
  if (job && (!sseSource || sseSource.readyState === EventSource.CLOSED)) connectSSE(job.id)
})

onMounted(() => {
  refresh()
  pollInterval = setInterval(() => jobsStore.fetchJobs(), 8000)
})
onUnmounted(() => {
  clearInterval(pollInterval)
  if (sseSource) sseSource.close()
})
</script>
