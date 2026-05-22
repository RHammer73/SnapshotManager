<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-white">Einstellungen</h1>
      <p class="text-sm text-gray-400 mt-1">Globale Konfiguration des SnapshotManagers</p>
    </div>

    <div class="card space-y-4">
      <h3 class="font-semibold text-white">Allgemein</h3>
      <div>
        <label class="label">App-Name</label>
        <input v-model="form.app_name" class="input" />
      </div>
      <div>
        <label class="label">Log-Aufbewahrung (Tage)</label>
        <input v-model="form.log_retention_days" type="number" class="input w-32" />
      </div>
    </div>

    <div class="card space-y-4">
      <h3 class="font-semibold text-white">Server</h3>
      <div class="bg-red-900/20 border border-red-800 rounded-lg p-4">
        <p class="text-sm text-red-300 font-medium mb-2">Backupserver herunterfahren</p>
        <p class="text-xs text-red-400/70 mb-3">Der Server wird sofort heruntergefahren. Alle laufenden Backups werden abgebrochen.</p>
        <button @click="confirmShutdown = true" class="btn-danger text-sm">Server herunterfahren</button>
      </div>
    </div>

    <div class="flex gap-3">
      <button @click="save" class="btn-primary" :disabled="saving">
        {{ saving ? 'Speichern...' : 'Einstellungen speichern' }}
      </button>
    </div>

    <div v-if="saved" class="bg-green-900/30 border border-green-800 rounded-lg px-4 py-3 text-green-300 text-sm">
      Einstellungen gespeichert
    </div>

    <!-- Shutdown Confirm -->
    <ConfirmModal
      v-if="confirmShutdown"
      title="Server herunterfahren?"
      message="Der Backupserver wird in 10 Sekunden heruntergefahren."
      confirm-label="Herunterfahren"
      @confirm="shutdown"
      @cancel="confirmShutdown = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api.js'
import ConfirmModal from '@/components/ConfirmModal.vue'

const form = ref({ app_name: '', log_retention_days: '90' })
const saving = ref(false)
const saved = ref(false)
const confirmShutdown = ref(false)

async function load() {
  const { data } = await api.get('/settings')
  for (const s of data) form.value[s.key] = s.value
}

async function save() {
  saving.value = true
  try {
    await api.put('/settings', { settings: form.value })
    saved.value = true
    setTimeout(() => saved.value = false, 3000)
  } finally {
    saving.value = false
  }
}

async function shutdown() {
  confirmShutdown.value = false
  await api.post('/settings/system/shutdown')
  alert('Server wird heruntergefahren...')
}

onMounted(load)
</script>
