import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/client'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<{ id: number; username: string; display_name: string; role: string } | null>(
    JSON.parse(localStorage.getItem('user') || 'null'),
  )

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.data.access_token
    userInfo.value = {
      id: res.data.user_id,
      username: res.data.username,
      display_name: res.data.username,
      role: res.data.role,
    }
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(userInfo.value))
  }

  async function register(username: string, password: string, displayName?: string) {
    const res = await authApi.register({ username, password, display_name: displayName })
    token.value = res.data.access_token
    userInfo.value = {
      id: res.data.user_id,
      username: res.data.username,
      display_name: displayName || res.data.username,
      role: res.data.role,
    }
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(userInfo.value))
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, userInfo, isLoggedIn, isAdmin, login, register, logout }
})
