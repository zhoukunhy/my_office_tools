import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '速用工具箱', tab: 'home' }
  },
  {
    path: '/tools',
    name: 'tools',
    component: () => import('@/views/ToolsView.vue'),
    meta: { title: '工具大全', tab: 'tools' }
  },
  {
    path: '/resume',
    name: 'resume',
    component: () => import('@/views/ResumeView.vue'),
    meta: { title: '简历制作' }
  },
  {
    path: '/ai-ppt',
    name: 'ai-ppt',
    component: () => import('@/views/AiPptView.vue'),
    meta: { title: 'AI 生成PPT' }
  },
  {
    path: '/interview',
    name: 'interview',
    component: () => import('@/views/InterviewView.vue'),
    meta: { title: '面试题库' }
  },
  {
    path: '/favorites',
    name: 'favorites',
    component: () => import('@/views/FavoritesView.vue'),
    meta: { title: '我的收藏', tab: 'favorites' }
  },
  {
    path: '/me',
    name: 'me',
    component: () => import('@/views/MeView.vue'),
    meta: { title: '个人中心', tab: 'me' }
  },
  {
    path: '/tool/:slug',
    name: 'tool',
    component: () => import('@/views/ToolRunnerView.vue'),
    meta: { title: '工具', tab: 'tools' }
  },
  {
    // 保留 about 路由但不挂任何入口（后续按需在个人中心内部跳转）
    path: '/about',
    name: 'about',
    component: () => import('@/views/AboutView.vue'),
    meta: { title: '关于本站', hidden: true }
  },
  {
    path: '/system',
    name: 'system',
    component: () => import('@/views/SystemView.vue'),
    meta: { title: '系统效率工具推荐', hidden: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

const BASE_TITLE = '速用工具箱'
router.afterEach((to) => {
  const t = to.meta.title as string | undefined
  document.title = t ? `${t} · ${BASE_TITLE}` : BASE_TITLE
})

export default router
