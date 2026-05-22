<template>
  <div class="card">
    <div v-if="loading" class="text-center py-8 text-gray-500 text-sm">Lade VMs...</div>
    <div v-else-if="vms.length === 0" class="text-center py-8 text-gray-500 text-sm">
      Keine VMs gefunden. Klicke "VMs einlesen" um den Host zu scannen.
    </div>
    <div v-else>
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm text-gray-400">{{ vms.length }} VMs gefunden, {{ enabledCount }} ausgewählt</span>
        <div class="flex gap-2">
          <button @click="selectAll(true)" class="text-xs text-brand-400 hover:text-brand-300">Alle</button>
          <span class="text-gray-700">·</span>
          <button @click="selectAll(false)" class="text-xs text-gray-500 hover:text-gray-300">Keine</button>
        </div>
      </div>

      <draggable
        v-model="vms"
        item-key="id"
        handle=".drag-handle"
        @end="onReorder"
      >
        <template #item="{ element: vm }">
          <div class="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0 group">
            <!-- Drag handle -->
            <div class="drag-handle cursor-grab mt-1 text-gray-700 hover:text-gray-500">
              <Bars3Icon class="w-4 h-4" />
            </div>

            <!-- Enable toggle -->
            <button
              @click="toggleVm(vm)"
              class="mt-0.5 relative inline-flex h-4 w-7 shrink-0 rounded-full transition-colors"
              :class="vm.enabled ? 'bg-brand-600' : 'bg-gray-700'"
            >
              <span
                class="inline-block h-3 w-3 mt-0.5 ml-0.5 rounded-full bg-white shadow transition-transform"
                :class="vm.enabled ? 'translate-x-3' : 'translate-x-0'"
              />
            </button>

            <!-- VM Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <span class="font-medium text-sm text-white truncate">{{ vm.name }}</span>
                <span class="badge-gray text-xs">{{ vm.vm_type }}</span>
                <span class="text-xs text-gray-600">vmid: {{ vm.vmid }}</span>
                <span v-if="vm.last_backup_at" class="text-xs text-gray-600 ml-auto">
                  Letztes Backup: {{ formatDate(vm.last_backup_at) }}
                </span>
              </div>

              <div v-if="vm.enabled" class="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div>
                  <label class="label">Max. Backups</label>
                  <input
                    v-model.number="vm.retention_count"
                    type="number" min="1" max="365"
                    class="input py-1 text-xs"
                    @change="saveVm(vm)"
                  />
                </div>
                <div>
                  <label class="label">Max. Alter (Tage)</label>
                  <input
                    v-model.number="vm.retention_days"
                    type="number" min="1" max="3650"
                    class="input py-1 text-xs"
                    @change="saveVm(vm)"
                  />
                </div>
                <div class="col-span-2">
                  <label class="label">ZFS Datasets</label>
                  <p class="text-xs text-gray-500 font-mono truncate mt-1">
                    {{ formatDatasets(vm.zfs_datasets) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </template>
      </draggable>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Bars3Icon } from '@heroicons/vue/24/outline'
import draggable from 'vuedraggable'
import api from '@/api.js'

const props = defineProps({ hostId: { type: Number, required: true } })
const vms = ref([])
const loading = ref(false)

const enabledCount = computed(() => vms.value.filter(v => v.enabled).length)

function formatDate(d) { return d ? new Date(d).toLocaleDateString('de-DE') : '—' }
function formatDatasets(ds) {
  try { return JSON.parse(ds || '[]').join(', ') || 'Keine Datasets gefunden' }
  catch { return ds || '—' }
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/vms', { params: { host_id: props.hostId } })
    vms.value = data
  } finally {
    loading.value = false
  }
}

async function toggleVm(vm) {
  vm.enabled = !vm.enabled
  await api.put(`/vms/${vm.id}`, { enabled: vm.enabled, backup_order: vm.backup_order, retention_count: vm.retention_count, retention_days: vm.retention_days })
}

async function saveVm(vm) {
  await api.put(`/vms/${vm.id}`, { enabled: vm.enabled, backup_order: vm.backup_order, retention_count: vm.retention_count, retention_days: vm.retention_days })
}

async function onReorder() {
  const items = vms.value.map((vm, idx) => ({ id: vm.id, backup_order: idx + 1 }))
  await api.put('/vms/reorder', items)
}

function selectAll(val) {
  vms.value.forEach(vm => { vm.enabled = val; saveVm(vm) })
}

async function reload() { await load() }
defineExpose({ reload })

onMounted(load)
</script>
