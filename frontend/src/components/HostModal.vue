<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-xl w-full p-6 my-4">
        <h3 class="text-lg font-semibold text-white mb-5">{{ title }}</h3>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Name *</label>
              <input v-model="form.name" class="input" placeholder="Proxmox-01" />
            </div>
            <div>
              <label class="label">Beschreibung</label>
              <input v-model="form.description" class="input" placeholder="Optional" />
            </div>
            <div>
              <label class="label">IP-Adresse *</label>
              <input v-model="form.ip_address" class="input" placeholder="192.168.1.100" />
            </div>
            <div>
              <label class="label">SSH Port</label>
              <input v-model.number="form.ssh_port" type="number" class="input" />
            </div>
            <div>
              <label class="label">SSH Benutzer</label>
              <input v-model="form.ssh_user" class="input" />
            </div>
            <div>
              <label class="label">Authentifizierung</label>
              <select v-model="form.auth_type" class="input">
                <option value="password">Passwort</option>
                <option value="ssh_key">SSH-Key</option>
              </select>
            </div>
          </div>

          <div v-if="form.auth_type === 'password'">
            <label class="label">Passwort</label>
            <input v-model="form.ssh_password" type="password" class="input" />
          </div>
          <div v-else>
            <label class="label">Privater SSH-Key</label>
            <textarea v-model="form.ssh_private_key" class="input font-mono text-xs" rows="5" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">ZFS Pool (Proxmox) *</label>
              <input v-model="form.proxmox_pool" class="input font-mono" placeholder="rpool" />
            </div>
            <div>
              <label class="label">Backup Pool (lokal) *</label>
              <input v-model="form.backup_pool" class="input font-mono" placeholder="backup/proxmox01" />
            </div>
            <div>
              <label class="label">WoL MAC (optional)</label>
              <input v-model="form.wol_mac" class="input font-mono" placeholder="aa:bb:cc:dd:ee:ff" />
            </div>
          </div>
        </div>

        <div v-if="error" class="mt-3 bg-red-900/30 border border-red-800 rounded-lg px-3 py-2 text-red-300 text-sm">
          {{ error }}
        </div>

        <div class="flex gap-3 justify-end mt-6">
          <button @click="emit('close')" class="btn-secondary">Abbrechen</button>
          <button @click="save" class="btn-primary" :disabled="saving">
            {{ saving ? 'Speichern...' : 'Anlegen' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ title: { type: String, default: 'Host anlegen' } })
const emit = defineEmits(['save', 'close'])

const form = ref({
  name: '', description: '', ip_address: '',
  ssh_port: 22, ssh_user: 'root',
  auth_type: 'password', ssh_password: '', ssh_private_key: '',
  proxmox_pool: 'rpool', backup_pool: '', wol_mac: '',
})
const saving = ref(false)
const error = ref('')

async function save() {
  if (!form.value.name || !form.value.ip_address || !form.value.backup_pool) {
    error.value = 'Bitte alle Pflichtfelder ausfüllen'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await emit('save', { ...form.value })
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>
