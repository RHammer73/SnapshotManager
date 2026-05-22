import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api.js'

export const useHostsStore = defineStore('hosts', () => {
  const hosts = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchHosts() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/hosts')
      hosts.value = data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createHost(payload) {
    const { data } = await api.post('/hosts', payload)
    hosts.value.push(data)
    return data
  }

  async function updateHost(id, payload) {
    const { data } = await api.put(`/hosts/${id}`, payload)
    const idx = hosts.value.findIndex(h => h.id === id)
    if (idx !== -1) hosts.value[idx] = data
    return data
  }

  async function deleteHost(id) {
    await api.delete(`/hosts/${id}`)
    hosts.value = hosts.value.filter(h => h.id !== id)
  }

  async function discoverVMs(hostId) {
    const { data } = await api.post(`/hosts/${hostId}/discover-vms`)
    return data
  }

  async function testConnection(hostId) {
    const { data } = await api.post(`/hosts/${hostId}/test-connection`)
    return data
  }

  return { hosts, loading, error, fetchHosts, createHost, updateHost, deleteHost, discoverVMs, testConnection }
})
