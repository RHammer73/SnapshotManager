<template>
  <div class="p-6 max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Proxmox Hosts</h1>
        <p class="text-sm text-gray-400 mt-1">Verwalte deine Proxmox-Instanzen</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <PlusIcon class="w-4 h-4" /> Neuer Host
      </button>
    </div>

    <!-- Fehler -->
    <div v-if="error" class="bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-red-300 text-sm">
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-16 text-gray-500">Lade Hosts...</div>

    <!-- Leer -->
    <div v-else-if="hosts.length === 0" class="card text-center py-16">
      <ServerIcon class="w-12 h-12 text-gray-700 mx-auto mb-4" />
      <p class="text-gray-400 font-medium">Noch kein Host angelegt</p>
      <p class="text-gray-600 text-sm mt-1">Erstelle deinen ersten Proxmox-Host</p>
      <button @click="showCreateModal = true" class="btn-primary mt-4">Host anlegen</button>
    </div>

    <!-- Host-Cards -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="host in hosts"
        :key="host.id"
        class="card hover:border-gray-700 transition-colors cursor-pointer group"
        @click="$router.push(`/hosts/${host.id}`)"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 bg-brand-600/20 rounded-lg flex items-center justify-center">
              <ServerIcon class="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h3 class="font-semibold text-white text-sm">{{ host.name }}</h3>
              <p class="text-xs text-gray-500">{{ host.ip_address }}:{{ host.ssh_port }}</p>
            </div>
          </div>
          <span class="badge-gray text-xs">{{ host.auth_type === 'ssh_key' ? 'SSH-Key' : 'Passwort' }}</span>
        </div>

        <div class="space-y-1.5 text-xs text-gray-500">
          <div class="flex gap-2">
            <span class="text-gray-600">Proxmox Pool:</span>
            <span class="text-gray-300 font-mono">{{ host.proxmox_pool }}</span>
          </div>
          <div class="flex gap-2">
            <span class="text-gray-600">Backup Pool:</span>
            <span class="text-gray-300 font-mono">{{ host.backup_pool }}</span>
          </div>
          <div v-if="host.description" class="text-gray-500 truncate pt-1">{{ host.description }}</div>
        </div>

        <div class="flex items-center justify-between mt-4 pt-3 border-t border-gray-800">
          <RouterLink
            :to="`/hosts/${host.id}`"
            class="text-xs text-brand-400 hover:text-brand-300 font-medium"
            @click.stop
          >
            Konfigurieren →
          </RouterLink>
          <button
            @click.stop="confirmDelete(host)"
            class="text-xs text-gray-600 hover:text-red-400 transition-colors"
          >
            Löschen
          </button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <HostModal
      v-if="showCreateModal"
      title="Neuen Host anlegen"
      @save="onCreateHost"
      @close="showCreateModal = false"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      v-if="deleteTarget"
      :title="`Host '${deleteTarget.name}' löschen?`"
      message="Alle VMs, Snapshots und Schedules dieses Hosts werden ebenfalls gelöscht."
      confirm-label="Löschen"
      @confirm="onDeleteHost"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { PlusIcon, ServerIcon } from '@heroicons/vue/24/outline'
import { useHostsStore } from '@/stores/hosts.js'
import HostModal from '@/components/HostModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

const store = useHostsStore()
const hosts = computed(() => store.hosts)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

const showCreateModal = ref(false)
const deleteTarget = ref(null)

async function onCreateHost(data) {
  await store.createHost(data)
  showCreateModal.value = false
}

function confirmDelete(host) {
  deleteTarget.value = host
}

async function onDeleteHost() {
  await store.deleteHost(deleteTarget.value.id)
  deleteTarget.value = null
}

onMounted(() => store.fetchHosts())
</script>
