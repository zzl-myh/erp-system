import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserInfo, getMyPermissions } from '@/api/user'
import type { LoginForm, UserInfo } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)
  const permissions = ref<string[]>([])

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '')
  const name = computed(() => userInfo.value?.name || userInfo.value?.username || '')
  const roles = computed(() => userInfo.value?.roles?.map((r: { code: string }) => r.code) || [])
  const isAdmin = computed(() => roles.value.includes('ADMIN'))

  // 检查是否有权限
  function hasPermission(perm: string): boolean {
    if (isAdmin.value) return true
    return permissions.value.includes(perm)
  }

  // 检查是否有任一权限
  function hasAnyPermission(perms: string[]): boolean {
    if (isAdmin.value) return true
    return perms.some(p => permissions.value.includes(p))
  }

  // 登录
  async function login(form: LoginForm) {
    const res = await loginApi(form)
    if (res.success && res.data) {
      token.value = res.data.access_token
      localStorage.setItem('token', res.data.access_token)
      // 登录成功后获取用户信息和权限
      await fetchUserInfo()
      await fetchPermissions()
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

  // 获取用户权限
  async function fetchPermissions() {
    const res = await getMyPermissions()
    if (res.success && res.data) {
      permissions.value = res.data
    }
  }

  // 登出
  function logout() {
    token.value = ''
    userInfo.value = null
    permissions.value = []
    localStorage.removeItem('token')
  }

  return {
    token,
    userInfo,
    permissions,
    isLoggedIn,
    username,
    name,
    roles,
    isAdmin,
    hasPermission,
    hasAnyPermission,
    login,
    fetchUserInfo,
    fetchPermissions,
    logout,
  }
})
