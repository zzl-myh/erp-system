import { defineStore } from 'pinia'
import { ref } from 'vue'

interface MenuItem {
  path: string
  title: string
  icon?: string
}

export const useAppStore = defineStore('app', () => {
  // 侧边栏折叠状态
  const sidebarCollapsed = ref(false)

  // 菜单列表
  const menuList = ref<MenuItem[]>([
    { path: '/dashboard', title: '仪表盘', icon: 'Odometer' },
    { path: '/user', title: '用户管理', icon: 'User' },
    { path: '/role', title: '角色管理', icon: 'Avatar' },
    { path: '/org', title: '组织管理', icon: 'OfficeBuilding' },
    { path: '/item', title: '商品管理', icon: 'Goods' },
    { path: '/stock', title: '库存管理', icon: 'Box' },
    { path: '/order', title: '订单管理', icon: 'Document' },
    { path: '/member', title: '会员管理', icon: 'UserFilled' },
    { path: '/purchase', title: '采购管理', icon: 'ShoppingCart' },
    { path: '/production', title: '生产管理', icon: 'Setting' },
  ])

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    sidebarCollapsed,
    menuList,
    toggleSidebar,
  }
})
