import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api.js'

export const useSchedulesStore = defineStore('schedules', () => {
  const schedules = ref([])
  const loading = ref(false)

  async function fetchSchedules(hostId = null) {
    loading.value = true
    try {
      const params = hostId ? { host_id: hostId } : {}
      const { data } = await api.get('/schedules', { params })
      schedules.value = data
    } finally {
      loading.value = false
    }
  }

  async function createSchedule(payload) {
    const { data } = await api.post('/schedules', payload)
    schedules.value.push(data)
    return data
  }

  async function updateSchedule(id, payload) {
    const { data } = await api.put(`/schedules/${id}`, payload)
    const idx = schedules.value.findIndex(s => s.id === id)
    if (idx !== -1) schedules.value[idx] = data
    return data
  }

  async function deleteSchedule(id) {
    await api.delete(`/schedules/${id}`)
    schedules.value = schedules.value.filter(s => s.id !== id)
  }

  return { schedules, loading, fetchSchedules, createSchedule, updateSchedule, deleteSchedule }
})
