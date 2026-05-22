<template>
  <div class="card flex items-center gap-4">
    <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" :class="bgClass">
      <component :is="iconComponent" class="w-5 h-5" :class="textClass" />
    </div>
    <div>
      <div class="text-2xl font-bold text-white">{{ value }}</div>
      <div class="text-xs text-gray-500">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  ServerIcon, CubeIcon, ClockIcon, ExclamationCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  label: String,
  value: [Number, String],
  icon: String,
  color: { type: String, default: 'brand' },
})

const icons = { server: ServerIcon, cube: CubeIcon, clock: ClockIcon, exclamation: ExclamationCircleIcon }
const iconComponent = computed(() => icons[props.icon] || ServerIcon)

const bgClass = computed(() => ({
  brand: 'bg-brand-600/20', sky: 'bg-sky-600/20',
  violet: 'bg-violet-600/20', red: 'bg-red-600/20',
}[props.color]))
const textClass = computed(() => ({
  brand: 'text-brand-400', sky: 'text-sky-400',
  violet: 'text-violet-400', red: 'text-red-400',
}[props.color]))
</script>
