<template>
  <span class="relative flex h-2.5 w-2.5 shrink-0">
    <span v-if="status === 'running'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
    <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="dotClass" />
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const dotClass = computed(() => ({
  pending: 'bg-yellow-500',
  running: 'bg-brand-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
}[props.status] || 'bg-gray-500'))
</script>
