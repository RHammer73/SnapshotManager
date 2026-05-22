<template>
  <div class="min-h-screen flex">
    <!-- Sidebar -->
    <aside class="w-56 bg-gray-900 border-r border-gray-800 flex flex-col fixed h-full z-20">
      <!-- Logo -->
      <div class="px-5 py-5 border-b border-gray-800">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <ServerStackIcon class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-white text-sm">SnapshotManager</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(item.to)
            ? 'bg-brand-600/20 text-brand-400'
            : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <!-- Backup läuft Indicator -->
      <div v-if="backupRunning" class="px-3 py-3 border-t border-gray-800">
        <div class="flex items-center gap-2 px-3 py-2 bg-brand-600/10 rounded-lg border border-brand-800">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
          </span>
          <span class="text-xs text-brand-400 font-medium">Backup läuft</span>
        </div>
      </div>

      <!-- Version -->
      <div class="px-5 py-3 border-t border-gray-800">
        <span class="text-xs text-gray-600">v1.0.0</span>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 ml-56 min-h-screen">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  ServerStackIcon,
  HomeIcon,
  ServerIcon,
  ClockIcon,
  CalendarIcon,
  Cog6ToothIcon,
} from '@heroicons/vue/24/outline'
import api from '@/api.js'

const route = useRoute()
const backupRunning = ref(false)
let statusInterval = null

const navItems = [
  { to: '/',          label: 'Dashboard',  icon: HomeIcon },
  { to: '/hosts',     label: 'Hosts',      icon: ServerIcon },
  { to: '/jobs',      label: 'Jobs',       icon: ClockIcon },
  { to: '/schedules', label: 'Schedules',  icon: CalendarIcon },
  { to: '/settings',  label: 'Einstellungen', icon: Cog6ToothIcon },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function checkStatus() {
  try {
    const { data } = await api.get('/jobs/status/running')
    backupRunning.value = data.running
  } catch {
    // ignore
  }
}

onMounted(() => {
  checkStatus()
  statusInterval = setInterval(checkStatus, 5000)
})

onUnmounted(() => {
  clearInterval(statusInterval)
})
</script>
