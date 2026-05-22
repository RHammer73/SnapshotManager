<template>
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-xs font-medium text-gray-400">{{ label }}</span>
      <span class="text-xs font-bold" :class="colorClass">{{ value }}%</span>
    </div>
    <div class="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
      <div
        class="h-full rounded-full transition-all duration-300 ease-out relative overflow-hidden"
        :class="barClass"
        :style="{ width: `${Math.min(value, 100)}%` }"
      >
        <!-- Animated shine -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: 'brand' },
})

const colorClass = computed(() => ({
  brand: 'text-brand-400',
  sky: 'text-sky-400',
  green: 'text-green-400',
  red: 'text-red-400',
}[props.color] || 'text-brand-400'))

const barClass = computed(() => ({
  brand: 'bg-gradient-to-r from-brand-600 to-brand-400',
  sky: 'bg-gradient-to-r from-sky-600 to-sky-400',
  green: 'bg-gradient-to-r from-green-600 to-green-400',
  red: 'bg-gradient-to-r from-red-600 to-red-400',
}[props.color] || 'bg-gradient-to-r from-brand-600 to-brand-400'))
</script>
