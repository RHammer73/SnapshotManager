<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div class="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-lg w-full p-6">
        <h3 class="text-lg font-semibold text-white mb-5">
          {{ schedule ? 'Schedule bearbeiten' : 'Neuer Schedule' }}
        </h3>

        <div class="space-y-4">
          <div>
            <label class="label">Name *</label>
            <input v-model="form.name" class="input" placeholder="Nachtbackup" />
          </div>
          <div>
            <label class="label">Host *</label>
            <select v-model.number="form.host_id" class="input">
              <option value="">Host wählen...</option>
              <option v-for="h in hosts" :key="h.id" :value="h.id">{{ h.name }}</option>
            </select>
          </div>
          <div>
            <label class="label">Cron-Ausdruck *</label>
            <input v-model="form.cron_expression" class="input font-mono" placeholder="0 2 * * *" />
            <p class="text-xs text-gray-600 mt-1">Format: Minute Stunde Tag Monat Wochentag · Beispiel: <span class="font-mono text-gray-500">0 2 * * *</span> = täglich 02:00 Uhr</p>
          </div>

          <!-- Schnellauswahl -->
          <div class="flex gap-2 flex-wrap">
            <button v-for="p in presets" :key="p.label" @click="form.cron_expression = p.cron" class="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 px-2 py-1 rounded border border-gray-700">{{ p.label }}</button>
          </div>

          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="form.enabled" class="w-4 h-4 accent-brand-500" />
              <span class="text-sm text-gray-300">Aktiviert</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="form.shutdown_after" class="w-4 h-4 accent-yellow-500" />
              <span class="text-sm text-gray-300">Server nach Backup herunterfahren</span>
            </label>
          </div>
        </div>

        <div v-if="error" class="mt-3 bg-red-900/30 border border-red-800 rounded-lg px-3 py-2 text-red-300 text-sm">{{ error }}</div>

        <div class="flex gap-3 justify-end mt-6">
          <button @click="emit('close')" class="btn-secondary">Abbrechen</button>
          <button @click="save" class="btn-primary" :disabled="saving">{{ saving ? 'Speichern...' : 'Speichern' }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  schedule: Object,
  hosts: Array,
})
const emit = defineEmits(['save', 'close'])

const form = ref({
  name: '', host_id: '', cron_expression: '0 2 * * *',
  enabled: true, shutdown_after: false,
})
const saving = ref(false)
const error = ref('')

const presets = [
  { label: 'Tägl. 01:00', cron: '0 1 * * *' },
  { label: 'Tägl. 02:00', cron: '0 2 * * *' },
  { label: 'Tägl. 03:00', cron: '0 3 * * *' },
  { label: 'Sonntag 01:00', cron: '0 1 * * 0' },
  { label: 'Mo-Fr 22:00', cron: '0 22 * * 1-5' },
]

watch(() => props.schedule, (s) => {
  if (s) form.value = { name: s.name, host_id: s.host_id, cron_expression: s.cron_expression, enabled: s.enabled, shutdown_after: s.shutdown_after }
}, { immediate: true })

async function save() {
  if (!form.value.name || !form.value.host_id || !form.value.cron_expression) {
    error.value = 'Bitte alle Pflichtfelder ausfüllen'
    return
  }
  saving.value = true
  error.value = ''
  try { emit('save', { ...form.value }) }
  catch (e) { error.value = e.message }
  finally { saving.value = false }
}
</script>
