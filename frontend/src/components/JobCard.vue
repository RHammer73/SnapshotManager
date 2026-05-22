<template>
  <div class="flex items-center justify-between py-3 px-4 bg-gray-800/50 rounded-lg border border-gray-800">
    <div class="flex items-center gap-3">
      <StatusDot :status="job.status" />
      <div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-white">Job #{{ job.id }}</span>
          <span v-if="hostName" class="badge-gray text-xs">{{ hostName }}</span>
          <span class="badge-gray text-xs capitalize">{{ job.triggered_by }}</span>
        </div>
        <div class="text-xs text-gray-500 mt-0.5">
          {{ formatDate(job.started_at) }}
          <span v-if="job.finished_at"> · {{ duration(job.started_at, job.finished_at) }}</span>
        </div>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span :class="statusBadge(job.status)" class="text-xs">{{ statusLabel(job.status) }}</span>
      <RouterLink v-if="showLink" :to="`/jobs`" class="text-xs text-brand-400 hover:text-brand-300">Details →</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import StatusDot from './StatusDot.vue'

defineProps({
  job: Object,
  hostName: String,
  showLink: Boolean,
})

function formatDate(d) { return d ? new Date(d).toLocaleString('de-DE') : '—' }
function duration(start, end) {
  const s = Math.floor((new Date(end) - new Date(start)) / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`
}
function statusLabel(s) { return { pending: 'Ausstehend', running: 'Läuft', completed: 'Abgeschlossen', failed: 'Fehler', cancelled: 'Abgebrochen' }[s] || s }
function statusBadge(s) { return { pending: 'badge-yellow', running: 'badge-blue', completed: 'badge-green', failed: 'badge-red', cancelled: 'badge-gray' }[s] || 'badge-gray' }
</script>
