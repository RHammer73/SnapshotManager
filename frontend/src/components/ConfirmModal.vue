<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div class="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-md w-full p-6">
        <h3 class="text-lg font-semibold text-white mb-2">{{ title }}</h3>
        <p class="text-sm text-gray-400 mb-6">{{ message }}</p>
        <div class="flex gap-3 justify-end">
          <button @click="emit('cancel')" class="btn-secondary">Abbrechen</button>
          <button @click="emit('confirm')" class="btn-danger">{{ confirmLabel }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  title: String,
  message: String,
  confirmLabel: { type: String, default: 'Bestätigen' },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>
