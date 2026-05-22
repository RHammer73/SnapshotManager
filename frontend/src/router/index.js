import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',            name: 'Dashboard',  component: () => import('@/views/Dashboard.vue') },
  { path: '/hosts',       name: 'Hosts',      component: () => import('@/views/Hosts.vue') },
  { path: '/hosts/:id',   name: 'HostDetail', component: () => import('@/views/HostDetail.vue') },
  { path: '/jobs',        name: 'Jobs',        component: () => import('@/views/Jobs.vue') },
  { path: '/schedules',   name: 'Schedules',   component: () => import('@/views/Schedules.vue') },
  { path: '/settings',    name: 'Settings',    component: () => import('@/views/Settings.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
