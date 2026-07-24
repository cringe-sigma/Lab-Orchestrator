import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../pages/Login.vue'),
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../pages/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/boards',
      name: 'Boards',
      component: () => import('../pages/Boards.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/bookings',
      name: 'Booking',
      component: () => import('../pages/Booking.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/experiments',
      name: 'Experiments',
      component: () => import('../pages/Experiments.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/ai-agent',
      name: 'AIAgent',
      component: () => import('../pages/AIAgent.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/permissions',
      name: 'Permissions',
      component: () => import('../pages/Permissions.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../pages/Admin.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/manual',
      name: 'UserManual',
      component: () => import('../pages/UserManual.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// 路由守卫 — 未登录跳转到登录页
router.beforeEach((to, _from) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { name: 'Login' }
  }
  // admin 页面检查角色
  if (to.meta.requiresAdmin) {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (user.role !== 'admin') {
      alert('此页面仅管理员可访问')
      return { name: 'Dashboard' }
    }
  }
})

export default router
