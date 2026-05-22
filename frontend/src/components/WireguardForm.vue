<template>
  <div class="space-y-4">
    <div v-if="!config" class="text-center py-8">
      <p class="text-gray-500 text-sm mb-4">Noch keine WireGuard-Konfiguration vorhanden</p>
      <button @click="startCreate" class="btn-primary">WireGuard konfigurieren</button>
    </div>

    <template v-else>
      <!-- Status -->
      <div class="flex items-center gap-3 mb-2">
        <span :class="isActive ? 'badge-green' : 'badge-gray'">
          {{ isActive ? 'Verbunden' : 'Getrennt' }}
        </span>
        <span class="text-sm text-gray-400 font-mono">{{ config.interface_name }}</span>
      </div>

      <!-- Form -->
      <div v-if="editing" class="space-y-3">
        <div>
          <label class="label">Interface-Name</label>
          <input v-model="form.interface_name" class="input font-mono" placeholder="wg-proxmox01" />
        </div>
        <div>
          <label class="label">WireGuard Konfiguration (wg-quick Format)</label>
          <textarea
            v-model="form.config_content"
            class="input font-mono text-xs leading-relaxed"
            rows="14"
            placeholder="[Interface]
PrivateKey = ...
Address = 10.0.0.2/24

[Peer]
PublicKey = ...
Endpoint = 1.2.3.4:51820
AllowedIPs = 10.0.0.1/32"
          />
        </div>
        <div class="flex gap-2">
          <button @click="save" class="btn-primary" :disabled="saving">{{ saving ? 'Speichern...' : 'Speichern' }}</button>
          <button @click="editing = false" class="btn-secondary">Abbrechen</button>
        </div>
      </div>

      <div v-else class="space-y-3">
        <!-- Config Vorschau -->
        <pre class="bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-400 font-mono overflow-auto max-h-40 whitespace-pre-wrap">{{ config.config_content }}</pre>

        <!-- Aktionen -->
        <div class="flex gap-2 flex-wrap">
          <button v-if="!isActive" @click="wgUp" class="btn-success" :disabled="toggling">
            <ArrowUpCircleIcon class="w-4 h-4" /> Verbinden
          </button>
          <button v-else @click="wgDown" class="btn-danger" :disabled="toggling">
            <ArrowDownCircleIcon class="w-4 h-4" /> Trennen
          </button>
          <button @click="editing = true" class="btn-secondary">Bearbeiten</button>
          <button @click="confirmDelete = true" class="btn-secondary text-red-400 hover:text-red-300">Löschen</button>
        </div>
      </div>
    </template>

    <!-- Create form (inline) -->
    <div v-if="creating" class="space-y-3 border-t border-gray-800 pt-4">
      <div>
        <label class="label">Interface-Name</label>
        <input v-model="newForm.interface_name" class="input font-mono" placeholder="wg-proxmox01" />
      </div>
      <div>
        <label class="label">WireGuard Konfiguration</label>
        <textarea v-model="newForm.config_content" class="input font-mono text-xs leading-relaxed" rows="12" placeholder="[Interface]&#10;PrivateKey = ...&#10;Address = 10.0.0.2/24&#10;&#10;[Peer]&#10;PublicKey = ...&#10;Endpoint = 1.2.3.4:51820&#10;AllowedIPs = 10.0.0.1/32" />
      </div>
      <div class="flex gap-2">
        <button @click="create" class="btn-primary" :disabled="saving">{{ saving ? 'Speichern...' : 'Anlegen' }}</button>
        <button @click="creating = false" class="btn-secondary">Abbrechen</button>
      </div>
    </div>

    <!-- Delete Confirm -->
    <ConfirmModal
      v-if="confirmDelete"
      title="WireGuard-Konfiguration löschen?"
      message="Das Interface wird getrennt und die Konfiguration gelöscht."
      confirm-label="Löschen"
      @confirm="deleteConfig"
      @cancel="confirmDelete = false"
    />

    <div v-if="errorMsg" class="bg-red-900/30 border border-red-800 rounded-lg px-3 py-2 text-red-300 text-sm">{{ errorMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowUpCircleIcon, ArrowDownCircleIcon } from '@heroicons/vue/24/outline'
import api from '@/api.js'
import ConfirmModal from './ConfirmModal.vue'

const props = defineProps({ hostId: { type: Number, required: true } })
const emit = defineEmits(['updated'])

const config = ref(null)
const editing = ref(false)
const creating = ref(false)
const saving = ref(false)
const toggling = ref(false)
const confirmDelete = ref(false)
const errorMsg = ref('')
const form = ref({ interface_name: '', config_content: '' })
const newForm = ref({ interface_name: '', config_content: '' })

const isActive = computed(() => config.value?.status === 'active')

async function load() {
  try {
    const { data } = await api.get('/wireguard', { params: { host_id: props.hostId } })
    config.value = data[0] || null
    if (config.value) form.value = { ...config.value }
  } catch {}
}

function startCreate() { creating.value = true }

async function create() {
  saving.value = true
  errorMsg.value = ''
  try {
    await api.post('/wireguard', { ...newForm.value, host_id: props.hostId })
    creating.value = false
    await load()
    emit('updated')
  } catch (e) { errorMsg.value = e.message }
  finally { saving.value = false }
}

async function save() {
  saving.value = true
  errorMsg.value = ''
  try {
    await api.put(`/wireguard/${config.value.id}`, { interface_name: form.value.interface_name, config_content: form.value.config_content })
    editing.value = false
    await load()
    emit('updated')
  } catch (e) { errorMsg.value = e.message }
  finally { saving.value = false }
}

async function wgUp() {
  toggling.value = true
  errorMsg.value = ''
  try { await api.post(`/wireguard/${config.value.id}/up`); await load(); emit('updated') }
  catch (e) { errorMsg.value = e.message }
  finally { toggling.value = false }
}

async function wgDown() {
  toggling.value = true
  try { await api.post(`/wireguard/${config.value.id}/down`); await load(); emit('updated') }
  catch (e) { errorMsg.value = e.message }
  finally { toggling.value = false }
}

async function deleteConfig() {
  await api.delete(`/wireguard/${config.value.id}`)
  config.value = null
  confirmDelete.value = false
  emit('updated')
}

onMounted(load)
</script>
