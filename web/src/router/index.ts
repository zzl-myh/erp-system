import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'
import { useUserStore } from '@/stores/user'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', noAuth: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/default.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      // 个人信息
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/user/profile.vue'),
        meta: { title: '个人信息', hidden: true }
      },
      // 用户管理
      {
        path: 'user',
        name: 'UserManage',
        component: () => import('@/views/user/index.vue'),
        meta: { title: '用户管理', icon: 'User', permissions: ['user:view'] }
      },
      // 角色管理
      {
        path: 'role',
        name: 'RoleManage',
        component: () => import('@/views/user/role.vue'),
        meta: { title: '角色管理', icon: 'Avatar', permissions: ['role:view'] }
      },
      // 组织管理
      {
        path: 'org',
        name: 'OrgManage',
        component: () => import('@/views/user/org.vue'),
        meta: { title: '组织管理', icon: 'OfficeBuilding', permissions: ['org:view'] }
      },
      // 商品管理
      {
        path: 'item',
        name: 'ItemManage',
        component: () => import('@/views/item/index.vue'),
        meta: { title: '商品管理', icon: 'Goods', permissions: ['item:view'] }
      },
      // 库存管理
      {
        path: 'stock',
        name: 'StockManage',
        component: () => import('@/views/stock/index.vue'),
        meta: { title: '库存管理', icon: 'Box', permissions: ['stock:view'] }
      },
      // 订单管理
      {
        path: 'order',
        name: 'OrderManage',
        component: () => import('@/views/order/index.vue'),
        meta: { title: '订单管理', icon: 'Document', permissions: ['order:view'] }
      },
      // 会员管理
      {
        path: 'member',
        name: 'MemberManage',
        component: () => import('@/views/member/index.vue'),
        meta: { title: '会员管理', icon: 'UserFilled', permissions: ['member:view'] }
      },
      // 采购管理
      {
        path: 'purchase',
        name: 'PurchaseManage',
        component: () => import('@/views/purchase/index.vue'),
        meta: { title: '采购管理', icon: 'ShoppingCart', permissions: ['purchase:view'] }
      },
      // 生产管理
      {
        path: 'production',
        name: 'ProductionManage',
        component: () => import('@/views/production/index.vue'),
        meta: { title: '生产管理', icon: 'Setting', permissions: ['production:view'] }
      },
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404', noAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  NProgress.start()
  document.title = `${to.meta.title || 'ERP'} - ERP管理系统`
  
  const userStore = useUserStore()
  const token = userStore.token
  
  if (to.meta.noAuth) {
    next()
  } else if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
