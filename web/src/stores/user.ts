import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserInfo } from '@/api/user'
import type { LoginForm, UserInfo } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '')

  // 登录
  async function login(form: LoginForm) {
    const res = await loginApi(form)
    if (res.success && res.data) {
      token.value = res.data.access_token
      localStorage.setItem('token', res.data.access_token)
      return true
    }
    return false
  }

  // 获取用户信息
  async function fetchUserInfo() {
    const res = await getUserInfo()
    if (res.success && res.data) {
      userInfo.value = res.data
    }
  }

  // 登出
  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    username,
    login,
    fetchUserInfo,
    logout,
  }
})
