import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/overview' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/overview',
      name: 'overview',
      component: () => import('../pages/OverviewPage.vue'),
      meta: { title: '存储概览' },
    },
    {
      path: '/tables/:id',
      name: 'table-heat',
      component: () => import('../pages/TableHeatPage.vue'),
      meta: { title: '表热度详情' },
    },
    {
      path: '/policies',
      name: 'policies',
      component: () => import('../pages/PolicyTrialPage.vue'),
      meta: { title: '策略与试算' },
    },
    {
      path: '/plans',
      name: 'plans',
      component: () => import('../pages/MigrationPlanPage.vue'),
      meta: { title: '迁移计划' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/overview' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

setupGuards(router)

export default router
