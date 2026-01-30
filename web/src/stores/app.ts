import { defineStore } from 'pinia'
import { ref } from 'vue'

interface MenuItem {
  path: string
  title: string
  icon?: string
  permissions?: string[]  // 所需权限（任一即可）
}

export const useAppStore = defineStore('app', () => {
  // 侧边栏折叠状态
  const sidebarCollapsed = ref(false)

  // 菜单列表
  const menuList = ref<MenuItem[]>([
    { path: '/dashboard', title: '仪表盘', icon: 'Odometer' },
    { path: '/user', title: '用户管理', icon: 'User', permissions: ['user:view'] },
    { path: '/role', title: '角色管理', icon: 'Avatar', permissions: ['role:view'] },
    { path: '/org', title: '组织管理', icon: 'OfficeBuilding', permissions: ['org:view'] },
    { path: '/item', title: '商品管理', icon: 'Goods', permissions: ['item:view'] },
    { path: '/stock', title: '库存管理', icon: 'Box', permissions: ['stock:view'] },
    { path: '/order', title: '订单管理', icon: 'Document', permissions: ['order:view'] },
    { path: '/member', title: '会员管理', icon: 'UserFilled', permissions: ['member:view'] },
    { path: '/purchase', title: '采购管理', icon: 'ShoppingCart', permissions: ['purchase:view'] },
    { path: '/production', title: '生产管理', icon: 'Setting', permissions: ['production:view'] },
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
