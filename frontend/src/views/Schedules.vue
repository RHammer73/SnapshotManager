<template>
  <div class="p-6 max-w-4xl mx-auto space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Schedules</h1>
        <p class="text-sm text-gray-400 mt-1">Automatische Backup-Zeitpläne</p>
      </div>
      <button @click="showModal = true" class="btn-primary">
        <PlusIcon class="w-4 h-4" /> Neuer Schedule
      </button>
    </div>

    <div v-if="schedules.length === 0" class="card text-center py-16">
      <CalendarIcon class="w-12 h-12 text-gray-700 mx-auto mb-4" />
      <p class="text-gray-400 font-medium">Keine Schedules konfiguriert</p>
      <p class="text-gray-600 text-sm mt-1">Erstelle einen automatischen Backup-Zeitplan</p>
      <button @click="showModal = true" class="btn-primary mt-4">Schedule anlegen</button>
    </div>

    <div v-else class="space-y-3">
      <div v-for="s in schedules" :key="s.id" class="card">
        <div class="flex items-start justify-between">
          <div class="flex items-start gap-4">
            <!-- Toggle -->
            <button
              @click="toggleSchedule(s)"
              class="mt-0.5 relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors"
              :class="s.enabled ? 'bg-brand-600' : 'bg-gray-700'"
            >
              <span
                class="inline-block h-4 w-4 mt-0.5 rounded-full bg-white shadow transition-transform"
                :class="s.enabled ? 'translate-x-4' : 'translate-x-0.5'"
              />
            </button>

            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="font-medium text-white">{{ s.name }}</h3>
                <span class="badge-gray">{{ hostName(s.host_id) }}</span>
                <span v-if="s.shutdown_after" class="badge-yellow">Server herunterfahren</span>
              </div>
              <div class="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span class="font-mono bg-gray-800 px-2 py-0.5 rounded">{{ s.cron_expression }}</span>
                <span>{{ cronDescription(s.cron_expression) }}</span>
              </div>
              <div class="flex gap-4 mt-1.5 text-xs text-gray-600">
                <span v-if="s.last_run_at">Letzter Lauf: {{ formatDate(s.last_run_at) }}</span>
                <span v-if="s.next_run_at">Nächster Lauf: <span class="text-gray-400">{{ formatDate(s.next_run_at) }}</span></span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button @click="editSchedule(s)" class="btn-secondary py-1 px-2.5 text-xs">Bearbeiten</button>
            <button @click="confirmDelete(s)" class="btn-danger py-1 px-2.5 text-xs">Löschen</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <ScheduleModal
      v-if="showModal"
      :schedule="editTarget"
      :hosts="hosts"
      @save="onSave"
      @close="closeModal"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      v-if="deleteTarget"
      :title="`Schedule '${deleteTarget.name}' löschen?`"
      message="Der Schedule wird dauerhaft entfernt."
      confirm-label="Löschen"
      @confirm="onDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { PlusIcon, CalendarIcon } from '@heroicons/vue/24/outline'
import { useSchedulesStore } from '@/stores/schedules.js'
import { useHostsStore } from '@/stores/hosts.js'
import ScheduleModal from '@/components/ScheduleModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

const schedulesStore = useSchedulesStore()
const hostsStore = useHostsStore()
const schedules = computed(() => schedulesStore.schedules)
const hosts = computed(() => hostsStore.hosts)

const showModal = ref(false)
const editTarget = ref(null)
const deleteTarget = ref(null)

function hostName(id) { return hosts.value.find(h => h.id === id)?.name || `#${id}` }
function formatDate(d) { return d ? new Date(d).toLocaleString('de-DE') : '—' }
function cronDescription(cron) {
  const [min, hour, day, month, dow] = cron.split(' ')
  if (min === '0' && day === '*' && month === '*' && dow === '*') return `Täglich um ${hour}:00 Uhr`
  if (day === '*' && month === '*' && dow !== '*') {
    const days = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
    return `Jeden ${days[parseInt(dow)] || dow} um ${hour}:${min} Uhr`
  }
  return cron
}

function editSchedule(s) { editTarget.value = { ...s }; showModal.value = true }
function closeModal() { showModal.value = false; editTarget.value = null }
function confirmDelete(s) { deleteTarget.value = s }

async function toggleSchedule(s) {
  await schedulesStore.updateSchedule(s.id, { enabled: !s.enabled })
}

async function onSave(data) {
  if (editTarget.value?.id) {
    await schedulesStore.updateSchedule(editTarget.value.id, data)
  } else {
    await schedulesStore.createSchedule(data)
  }
  closeModal()
}

async function onDelete() {
  await schedulesStore.deleteSchedule(deleteTarget.value.id)
  deleteTarget.value = null
}

onMounted(async () => {
  await Promise.all([hostsStore.fetchHosts(), schedulesStore.fetchSchedules()])
})
</script>
