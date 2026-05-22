<template>
  <div class="p-6 max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <button @click="$router.back()" class="btn-secondary py-1.5 px-3">
        <ArrowLeftIcon class="w-4 h-4" /> Zurück
      </button>
      <div>
        <h1 class="text-2xl font-bold text-white">{{ host?.name }}</h1>
        <p class="text-sm text-gray-400">{{ host?.ip_address }}</p>
      </div>
    </div>

    <div v-if="!host" class="text-center py-16 text-gray-500">Lade Host...</div>

    <template v-else>
      <!-- Tabs -->
      <div class="border-b border-gray-800">
        <nav class="flex gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors"
            :class="activeTab === tab.id
              ? 'border-brand-500 text-brand-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- Tab: Allgemein -->
      <div v-if="activeTab === 'general'" class="space-y-4">
        <div class="card">
          <h3 class="font-semibold text-white mb-4">Verbindung</h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Name</label>
              <input v-model="form.name" class="input" />
            </div>
            <div>
              <label class="label">Beschreibung</label>
              <input v-model="form.description" class="input" placeholder="Optional" />
            </div>
            <div>
              <label class="label">IP-Adresse</label>
              <input v-model="form.ip_address" class="input" />
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
            <div v-if="form.auth_type === 'password'">
              <label class="label">Passwort</label>
              <input v-model="form.ssh_password" type="password" class="input" placeholder="Neues Passwort (leer = unverändert)" />
            </div>
            <div v-if="form.auth_type === 'ssh_key'" class="col-span-2">
              <label class="label">Privater SSH-Key</label>
              <textarea v-model="form.ssh_private_key" class="input font-mono text-xs" rows="6" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----" />
            </div>
          </div>
        </div>

        <div class="card">
          <h3 class="font-semibold text-white mb-4">ZFS Konfiguration</h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">ZFS Pool (auf Proxmox)</label>
              <input v-model="form.proxmox_pool" class="input font-mono" placeholder="rpool" />
            </div>
            <div>
              <label class="label">Backup Pool (auf diesem Server)</label>
              <input v-model="form.backup_pool" class="input font-mono" placeholder="backup/proxmox01" />
            </div>
            <div>
              <label class="label">MAC-Adresse für WakeOnLan (optional)</label>
              <input v-model="form.wol_mac" class="input font-mono" placeholder="aa:bb:cc:dd:ee:ff" />
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <button @click="saveHost" class="btn-primary" :disabled="saving">
            {{ saving ? 'Speichern...' : 'Speichern' }}
          </button>
          <button @click="testConn" class="btn-secondary" :disabled="testing">
            {{ testing ? 'Teste...' : 'Verbindung testen' }}
          </button>
        </div>

        <div v-if="connTestResult" class="rounded-lg px-4 py-3 text-sm" :class="connTestResult.success ? 'bg-green-900/30 border border-green-800 text-green-300' : 'bg-red-900/30 border border-red-800 text-red-300'">
          <span v-if="connTestResult.success">Verbindung erfolgreich: {{ connTestResult.info }}</span>
          <span v-else>Fehler: {{ connTestResult.error }}</span>
        </div>
      </div>

      <!-- Tab: WireGuard -->
      <div v-if="activeTab === 'wireguard'" class="space-y-4">
        <div class="card">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold text-white">WireGuard VPN</h3>
            <div class="flex gap-2">
              <span :class="wgStatus === 'active' ? 'badge-green' : 'badge-gray'">
                {{ wgStatus === 'active' ? 'Verbunden' : 'Getrennt' }}
              </span>
            </div>
          </div>
          <WireguardForm :host-id="hostId" @updated="loadWgConfig" />
        </div>
      </div>

      <!-- Tab: VMs -->
      <div v-if="activeTab === 'vms'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-400">Wähle VMs aus und konfiguriere die Backup-Einstellungen</p>
          <div class="flex gap-2">
            <button @click="discoverVMs" class="btn-secondary" :disabled="discovering">
              <ArrowPathIcon class="w-4 h-4" :class="discovering ? 'animate-spin' : ''" />
              {{ discovering ? 'Lädt...' : 'VMs einlesen' }}
            </button>
            <button @click="startBackup" class="btn-primary" :disabled="backupRunning">
              <PlayIcon class="w-4 h-4" />
              Backup starten
            </button>
          </div>
        </div>

        <div v-if="discoverResult" class="bg-green-900/20 border border-green-800 rounded-lg px-4 py-2 text-sm text-green-300">
          {{ discoverResult.discovered }} VMs gefunden, {{ discoverResult.created }} neu angelegt, {{ discoverResult.updated }} aktualisiert
        </div>

        <VmTable :host-id="hostId" ref="vmTableRef" />
      </div>

      <!-- Tab: Verlauf -->
      <div v-if="activeTab === 'history'" class="space-y-3">
        <div v-if="hostJobs.length === 0" class="card text-center py-12 text-gray-500">Noch keine Backup-Jobs</div>
        <JobCard
          v-for="job in hostJobs"
          :key="job.id"
          :job="job"
          :host-name="host.name"
          show-link
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftIcon, ArrowPathIcon, PlayIcon } from '@heroicons/vue/24/outline'
import { useHostsStore } from '@/stores/hosts.js'
import { useJobsStore } from '@/stores/jobs.js'
import WireguardForm from '@/components/WireguardForm.vue'
import VmTable from '@/components/VmTable.vue'
import JobCard from '@/components/JobCard.vue'
import api from '@/api.js'

const route = useRoute()
const hostId = parseInt(route.params.id)
const hostsStore = useHostsStore()
const jobsStore = useJobsStore()

const activeTab = ref('general')
const tabs = [
  { id: 'general', label: 'Allgemein' },
  { id: 'wireguard', label: 'WireGuard' },
  { id: 'vms', label: 'VMs' },
  { id: 'history', label: 'Verlauf' },
]

const host = ref(null)
const form = ref({})
const saving = ref(false)
const testing = ref(false)
const discovering = ref(false)
const discoverResult = ref(null)
const connTestResult = ref(null)
const wgStatus = ref('inactive')
const vmTableRef = ref(null)
const backupRunning = computed(() => jobsStore.jobs.some(j => ['running', 'pending'].includes(j.status)))
const hostJobs = computed(() => jobsStore.jobs.filter(j => j.host_id === hostId))

async function loadHost() {
  const { data } = await api.get(`/hosts/${hostId}`)
  host.value = data
  form.value = { ...data, ssh_password: '', ssh_private_key: '' }
}

async function loadWgConfig() {
  try {
    const { data } = await api.get('/wireguard', { params: { host_id: hostId } })
    wgStatus.value = data[0]?.status || 'inactive'
  } catch {}
}

async function saveHost() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.ssh_password) delete payload.ssh_password
    if (!payload.ssh_private_key) delete payload.ssh_private_key
    await hostsStore.updateHost(hostId, payload)
    await loadHost()
  } finally {
    saving.value = false
  }
}

async function testConn() {
  testing.value = true
  connTestResult.value = null
  try {
    connTestResult.value = await hostsStore.testConnection(hostId)
  } catch (e) {
    connTestResult.value = { success: false, error: e.message }
  } finally {
    testing.value = false
  }
}

async function discoverVMs() {
  discovering.value = true
  discoverResult.value = null
  try {
    discoverResult.value = await hostsStore.discoverVMs(hostId)
    if (vmTableRef.value) await vmTableRef.value.reload()
  } catch (e) {
    alert(e.message)
  } finally {
    discovering.value = false
  }
}

async function startBackup() {
  try {
    await jobsStore.startJob(hostId, false)
    activeTab.value = 'history'
    await jobsStore.fetchJobs(hostId)
  } catch (e) {
    alert(e.message)
  }
}

onMounted(async () => {
  await Promise.all([loadHost(), hostsStore.fetchHosts(), jobsStore.fetchJobs(hostId), loadWgConfig()])
})
</script>
