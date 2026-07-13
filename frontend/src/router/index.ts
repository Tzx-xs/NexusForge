import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: Dashboard,
  },
  {
    path: '/bible',
    redirect: () => {
      const lastNovelId = localStorage.getItem('xy-last-novel')
      if (!lastNovelId) return '/'
      return `/workspace/${lastNovelId}/writing/1`
    },
  },
  {
    path: '/outline',
    redirect: () => {
      const lastNovelId = localStorage.getItem('xy-last-novel')
      if (!lastNovelId) return '/'
      return `/workspace/${lastNovelId}/writing/1`
    },
  },
  {
    path: '/workspace/:novelId',
    component: () => import('@/views/Workspace.vue'),
    children: [
      {
        path: '',
        redirect: 'writing/1',
      },
      {
        path: 'writing/:chapterId',
        name: 'writing',
        component: () => import('@/views/WritingPage.vue'),
      },
    ],
  },
  {
    path: '/characters',
    name: 'characters',
    component: () => import('@/views/CharactersPage.vue'),
    meta: { requiresNovel: true },
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('@/views/ReviewPage.vue'),
    meta: { requiresNovel: true },
  },
  {
    path: '/new-book',
    name: 'new-book',
    component: () => import('@/views/NewBookWizard.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/Settings.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  // 依赖 last-novel 的路由，缺少 novelId 时重定向到首页
  if (to.meta.requiresNovel) {
    const lastNovelId = localStorage.getItem('xy-last-novel')
    if (!lastNovelId) {
      next('/')
      return
    }
  }

  // 校验 workspace 路由的 novelId 参数
  if (to.params.novelId !== undefined) {
    const novelId = String(to.params.novelId)
    if (!novelId || novelId === 'undefined' || novelId === 'null') {
      next('/')
      return
    }
  }
  next()
})

router.onError((error) => {
  console.error('Router error:', error)
})

export default router
