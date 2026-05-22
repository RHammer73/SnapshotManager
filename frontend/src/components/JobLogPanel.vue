<template>
  <div>
    <div v-if="loading" class="text-xs text-gray-500 py-2">Lade Logs...</div>
    <div v-else-if="logs.length === 0" class="text-xs text-gray-500 py-2">Keine Log-Einträge</div>
    <div v-else class="bg-gray-950 border border-gray-800 rounded-lg p-3 space-y-0.5 font-mono text-xs max-h-64 overflow-y-auto">
      <div
        v-for="log in logs"
        :key="log.id"
        class="flex gap-2 leading-5"
        :class="{ 'text-red-400': log.level === 'error', 'text-yellow-400': log.level === 'warning', 'text-gray-300': log.level === 'info' }"
      >
        <span class="text-gray-600 shrink-0">{{ formatTime(log.timestamp) }}</span>
        <span class="uppercase text-[10px] shrink-0 pt-px w-10" :class="{ 'text-red-600': log.level === 'error', 'text-yellow-600': log.level === 'warning', 'text-gray-600': log.level === 'info' }">{{ log.level }}</span>
        <span>{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api.js'

const props = defineProps({ jobId: Number })
const logs = ref([])
const loading = ref(true)

function formatTime(d) {
  const dt = new Date(d)
  return `${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}:${String(dt.getSeconds()).padStart(2,'0')}`
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/jobs/${props.jobId}/logs`)
    logs.value = data
  } finally {
    loading.value = false
  }
})
</script>
