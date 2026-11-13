<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/authStore'

const auth = useAuthStore()

onMounted(() => {
  if (auth.isAuthenticated && !auth.user) void auth.restore()
})
</script>

<template>
  <router-view />
</template>
