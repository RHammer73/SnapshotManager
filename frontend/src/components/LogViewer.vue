<template>
  <div class="bg-gray-950 border border-gray-800 rounded-lg overflow-hidden">
    <div class="flex items-center justify-between px-3 py-2 border-b border-gray-800">
      <span class="text-xs font-medium text-gray-500">Live-Log</span>
      <button @click="emit('clear')" class="text-xs text-gray-600 hover:text-gray-400">Leeren</button>
    </div>
    <div ref="logEl" class="overflow-y-auto p-3 space-y-0.5 font-mono text-xs" :style="{ maxHeight: height }">
      <div
        v-for="(entry, i) in displayLogs"
        :key="i"
        class="flex gap-2 leading-5"
        :class="levelColor(entry.level)"
      >
        <span class="shrink-0 text-gray-600">{{ formatTime(entry.ts) }}</span>
        <span class="text-gray-500 shrink-0 uppercase text-[10px] pt-px">{{ entry.level }}</span>
        <span>{{ entry.message }}</span>
      </div>
      <div v-if="displayLogs.length === 0" class="text-gray-700 italic">Warte auf Log-Einträge...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  maxLines: { type: Number, default: 20 },
  height: { type: String, default: '160px' },
})
const emit = defineEmits(['clear'])
const logEl = ref(null)

const displayLogs = computed(() => props.logs.slice(-props.maxLines))

function levelColor(level) {
  return { info: 'text-gray-300', warning: 'text-yellow-400', error: 'text-red-400' }[level] || 'text-gray-300'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`
}

watch(() => props.logs.length, async () => {
  await nextTick()
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
})
</script>
