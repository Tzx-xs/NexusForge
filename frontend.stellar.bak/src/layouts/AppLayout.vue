<template>
  <div class="app-layout" :class="{ 'menu-open': userMenuVisible }">
    <!-- 左侧侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarStore.appSidebarCollapsed }">
      <!-- 品牌 Logo -->
      <div class="sidebar-brand">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" class="brand-icon">
          <defs>
            <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#7c6cbf"/>
              <stop offset="100%" stop-color="#c4b5fd"/>
            </linearGradient>
          </defs>
          <circle cx="12" cy="12" r="10" stroke="url(#brandGrad)" stroke-width="1.5" fill="var(--xy-brand-100)"/>
          <circle cx="12" cy="6" r="2" fill="var(--xy-brand-starlight)"/>
          <circle cx="7" cy="16" r="1.5" fill="var(--xy-brand-500)" opacity=".7"/>
          <circle cx="17" cy="14" r="1.5" fill="var(--xy-brand-500)" opacity=".7"/>
          <line x1="12" y1="6" x2="7" y2="16" stroke="var(--xy-brand-400)" stroke-width=".8" opacity=".5"/>
          <line x1="12" y1="6" x2="17" y2="14" stroke="var(--xy-brand-400)" stroke-width=".8" opacity=".5"/>
        </svg>
        <span class="brand-text sidebar-text">星渊笔</span>
      </div>

      <!-- 写作统计 -->
      <div class="sidebar-stats sidebar-text">
        <div class="stats-compact">
          <div class="stat-mini">
            <span class="stat-mini-value">—</span>
            <span class="stat-mini-label">今日字数</span>
          </div>
          <div class="stat-mini-divider"/>
          <div class="stat-mini">
            <span class="stat-mini-value">—</span>
            <span class="stat-mini-label">完稿率</span>
          </div>
          <div class="stat-mini-divider"/>
          <div class="stat-mini">
            <span class="stat-mini-value">—</span>
            <span class="stat-mini-label">连续创作</span>
          </div>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <a
          v-for="item in navItems"
          :key="item.key"
          href="#"
          class="nav-item"
          :class="{ active: activeModule === item.key }"
          @click.prevent="$emit('switch-module', item.key)"
        >
          <component :is="item.icon" class="nav-icon"/>
          <span class="sidebar-text">{{ item.label }}</span>
        </a>
      </nav>

      <!-- 底部功能区 -->
      <div class="sidebar-bottom">
        <a href="#" class="bottom-link" @click.prevent="showHelp">
          <Help class="icon-16"/>
          <span class="sidebar-text">帮助</span>
        </a>

        <!-- 用户区 -->
        <div ref="userBtnRef" class="user-area" @click="toggleUserMenu">
          <div class="user-avatar">{{ avatarChar }}</div>
          <div class="user-info sidebar-text">
            <p class="user-name">{{ displayName }}</p>
            <p class="user-tier">{{ profile.penName || '专业版' }}</p>
          </div>
          <ChevronUp v-if="userMenuVisible" class="user-arrow sidebar-text icon-14"/>
          <ChevronDown v-else class="user-arrow sidebar-text icon-14"/>
        </div>
      </div>
    </aside>

    <!-- 移动端侧边栏遮罩 -->
    <div
      v-if="isMobile && !sidebarStore.appSidebarCollapsed"
      class="sidebar-backdrop"
      @click="sidebarStore.setAppSidebarCollapsed(true)"
    />

    <!-- 用户菜单弹窗 -->
    <div
      v-if="userMenuVisible"
      ref="userMenuRef"
      class="user-menu xy-card-shimmer"
      :style="userMenuStyle"
    >
      <div class="menu-header">
        <div class="menu-avatar">{{ avatarChar }}</div>
        <div>
          <p class="menu-name">{{ displayName }}</p>
          <p class="menu-email">{{ profile.email || defaultProfile.email }}</p>
        </div>
      </div>
      <div class="menu-divider"/>
      <a class="menu-item" @click.prevent="goProfile">
        <User class="icon-14"/>
        个人资料
      </a>
      <div class="menu-item-wrap">
        <a class="menu-item" @click.stop.prevent="themeSwitcherRef?.toggleMenu()">
          <Sun v-if="themeStore.effectiveMode === 'dark' || themeStore.effectiveMode === 'abyss'" class="icon-14"/>
          <Moon v-else class="icon-14"/>
          切换主题
          <span class="menu-kbd">Ctrl+Shift+L</span>
        </a>
        <ThemeSwitcher ref="themeSwitcherRef" class="theme-switcher-below" />
      </div>
      <a class="menu-item" @click.prevent="goSettings">
        <Settings class="icon-14"/>
        设置
      </a>
      <div class="menu-divider"/>
      <a class="menu-item menu-danger" @click.prevent="logout">
        <Logout class="icon-14"/>
        退出登录
      </a>
    </div>

    <!-- 右侧主内容区 -->
    <main class="main-content">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="sidebar-toggle" aria-label="折叠侧栏" @click="toggleSidebar">
            <LayoutSidebarLeftCollapse v-if="!sidebarStore.appSidebarCollapsed" class="icon-16"/>
            <LayoutSidebarLeftExpand v-else class="icon-16"/>
          </button>
          <h1 class="module-title">{{ moduleTitle }}</h1>
        </div>
        <div class="topbar-right">
          <button ref="notifyBtnRef" class="topbar-btn" title="通知" @click.stop="toggleNotify">
          <Bell class="icon-16"/>
          <span v-if="unreadCount > 0" class="notify-dot">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
        </button>

        <!-- 通知中心下拉 -->
        <div
          v-if="notifyVisible"
          ref="notifyMenuRef"
          class="notify-dropdown xy-card-shimmer"
          @click.stop
        >
          <div class="notify-header">
            <span class="notify-title">通知</span>
            <div class="notify-actions">
              <button class="notify-action" @click="markAllRead">全部已读</button>
              <button class="notify-action" @click="clearNotifications">清空</button>
            </div>
          </div>
          <div class="notify-list">
            <div
              v-for="item in notifications"
              :key="item.id"
              class="notify-item"
              :class="{ unread: !item.read }"
            >
              <div class="notify-item-main">
                <p class="notify-item-title">{{ item.title }}</p>
                <p class="notify-item-msg">{{ item.message }}</p>
              </div>
              <span class="notify-item-time">{{ formatNotifyTime(item.time) }}</span>
            </div>
            <div v-if="notifications.length === 0" class="notify-empty">
              暂无通知
            </div>
          </div>
        </div>

          <span class="ai-status">
            <span class="status-dot"/>
            AI 在线
          </span>
        </div>
      </header>

      <!-- 模块内容 -->
    <div class="content-area">
      <slot/>
    </div>
  </main>

  <!-- 帮助中心弹窗 -->
  <XyDialog v-model="helpVisible" title="帮助中心" confirm-text="知道了">
    <div class="help-body">
      <div class="help-section">
        <div class="help-section-title">
          <Keyboard class="help-icon"/>
          常用快捷键
        </div>
        <div class="help-shortcuts">
          <div class="help-row">
            <span class="help-label">切换主题</span>
            <span class="help-kbd">Ctrl</span>
            <span class="help-kbd">Shift</span>
            <span class="help-kbd">L</span>
          </div>
          <div class="help-row">
            <span class="help-label">折叠侧边栏</span>
            <span class="help-kbd">点击左上角图标</span>
          </div>
          <div class="help-row">
            <span class="help-label">返回工作台</span>
            <span class="help-kbd">设置页左上角</span>
          </div>
        </div>
      </div>
      <div class="help-section">
        <div class="help-section-title">
          <Command class="help-icon"/>
          功能模块
        </div>
        <p class="help-text">新建小说：创建作品并导入大纲，开启创作流程。</p>
        <p class="help-text">我的小说：管理全部作品，支持封面上传、删除与分页浏览。</p>
        <p class="help-text">内容审查：检查章节质量，识别逻辑与文风问题。</p>
        <p class="help-text">世界观管理：可视化人物、地理、规则与剧情关系图。</p>
      </div>
      <div class="help-section">
        <div class="help-section-title">
          <InfoCircle class="help-icon"/>
          使用提示
        </div>
        <p class="help-text">AI 配置保存在设置页，密钥仅存储在本地浏览器中。</p>
        <p class="help-text">导出作品前，请先在设置中选择目标格式与是否包含元数据。</p>
      </div>
    </div>
  </XyDialog>

  <!-- 个人资料弹窗 -->
  <XyDialog
    v-model="profileVisible"
    title="个人资料"
    confirm-text="保存"
    cancel-text="取消"
    @confirm="saveProfile"
  >
    <div class="profile-body">
      <div class="profile-avatar-section">
        <div class="profile-avatar">{{ avatarChar }}</div>
        <p class="profile-avatar-hint">头像自动取用户名首字</p>
      </div>
      <div class="profile-form">
        <div class="profile-row">
          <label class="profile-label">用户名</label>
          <input v-model="profile.username" type="text" class="profile-input" placeholder="请输入用户名"/>
        </div>
        <div class="profile-row">
          <label class="profile-label">作者笔名</label>
          <input v-model="profile.penName" type="text" class="profile-input" placeholder="请输入笔名"/>
        </div>
        <div class="profile-row">
          <label class="profile-label">邮箱</label>
          <input v-model="profile.email" type="email" class="profile-input" placeholder="请输入邮箱"/>
        </div>
        <div class="profile-row">
          <label class="profile-label">个人简介</label>
          <textarea v-model="profile.bio" class="profile-textarea" rows="3" placeholder="一句话介绍你自己..."></textarea>
        </div>
      </div>
    </div>
  </XyDialog>
</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import { useSidebarStore } from '@/stores/sidebar'
import { ThemeSwitcher, XyDialog } from '@/components/common'
import {
  Plus,
  Book,
  Checkbox,
  Globe,
  LayoutSidebarLeftCollapse,
  LayoutSidebarLeftExpand,
  Settings,
  Help,
  ChevronDown,
  ChevronUp,
  User,
  Sun,
  Moon,
  Logout,
  Bell,
  Keyboard,
  Command,
  InfoCircle,
} from '@vicons/tabler'

const props = defineProps<{
  activeModule: string
}>()

defineEmits<{
  'switch-module': [module: string]
}>()

const router = useRouter()
const message = useMessage()
const themeStore = useThemeStore()
const sidebarStore = useSidebarStore()

const userMenuVisible = ref(false)
const userMenuStyle = ref({ left: '0px', top: '0px' })
const userBtnRef = ref<HTMLDivElement>()
const userMenuRef = ref<HTMLDivElement>()
const themeSwitcherRef = ref<{ toggleMenu: () => void } | null>(null)
const isMobile = ref(false)
const helpVisible = ref(false)

interface AppNotification {
  id: string
  title: string
  message: string
  time: string
  read: boolean
}

const notifyVisible = ref(false)
const notifyBtnRef = ref<HTMLButtonElement>()
const notifyMenuRef = ref<HTMLDivElement>()
const notifications = ref<AppNotification[]>([])
const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

interface UserProfile {
  username: string
  penName: string
  email: string
  bio: string
}

const defaultProfile: UserProfile = {
  username: '星渊作者',
  penName: '',
  email: 'author@xingyuan.bi',
  bio: '',
}

const profileVisible = ref(false)
const profile = ref<UserProfile>({ ...defaultProfile })
const displayName = computed(() => profile.value.username || defaultProfile.username)
const avatarChar = computed(() => {
  const name = displayName.value
  return name ? name.charAt(0) : '渊'
})

function checkMobile() {
  const mobile = window.innerWidth <= 768
  if (mobile && !isMobile.value) {
    sidebarStore.setAppSidebarCollapsed(true)
  }
  if (!mobile) {
    sidebarStore.setAppSidebarCollapsed(false)
  }
  isMobile.value = mobile
}

function toggleSidebar() {
  sidebarStore.toggleAppSidebar()
}

const navItems = [
  { key: 'new-novel', label: '新建小说', icon: Plus },
  { key: 'my-novels', label: '我的小说', icon: Book },
  { key: 'content-review', label: '内容审查', icon: Checkbox },
  { key: 'worldview', label: '世界观管理', icon: Globe },
]

const moduleTitles: Record<string, string> = {
  'new-novel': '新建小说',
  'my-novels': '我的小说',
  'content-review': '内容审查',
  'worldview': '世界观管理',
}

const moduleTitle = computed(() => moduleTitles[props.activeModule] ?? '')

function goSettings() {
  userMenuVisible.value = false
  router.push('/settings')
}

function showHelp() {
  helpVisible.value = true
}

function loadNotifications() {
  try {
    const saved = localStorage.getItem('xy-notifications')
    if (saved) {
      notifications.value = JSON.parse(saved)
      return
    }
  } catch (e) {
    console.error('Failed to load notifications:', e)
  }
  notifications.value = [
    {
      id: 'welcome',
      title: '欢迎使用星渊笔',
      message: '开始创建你的第一部小说，探索 AI 辅助创作。',
      time: new Date().toISOString(),
      read: false,
    },
  ]
  saveNotifications()
}

function saveNotifications() {
  try {
    localStorage.setItem('xy-notifications', JSON.stringify(notifications.value))
  } catch (e) {
    console.error('Failed to save notifications:', e)
  }
}

function toggleNotify() {
  notifyVisible.value = !notifyVisible.value
}

function markAllRead() {
  notifications.value.forEach((n) => {
    n.read = true
  })
  saveNotifications()
}

function clearNotifications() {
  notifications.value = []
  saveNotifications()
}

function formatNotifyTime(iso: string) {
  const date = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function loadProfile() {
  try {
    const saved = localStorage.getItem('xy-profile')
    if (saved) {
      const data = JSON.parse(saved)
      profile.value = { ...defaultProfile, ...data }
    }
  } catch (e) {
    console.error('Failed to load profile:', e)
  }
}

function saveProfile() {
  try {
    localStorage.setItem('xy-profile', JSON.stringify(profile.value))
    message.success('个人资料已保存')
    profileVisible.value = false
  } catch (e) {
    console.error('Failed to save profile:', e)
    message.error('保存失败')
  }
}

function goProfile() {
  userMenuVisible.value = false
  profileVisible.value = true
}

function logout() {
  userMenuVisible.value = false
  sessionStorage.removeItem('xy-api-key')
  localStorage.removeItem('xy-last-novel')
  message.success('已退出登录')
  router.push('/')
}

function toggleUserMenu() {
  userMenuVisible.value = !userMenuVisible.value
  if (userMenuVisible.value) {
    nextTick(updateMenuPosition)
  }
}

function updateMenuPosition() {
  const btn = userBtnRef.value
  const menu = userMenuRef.value
  if (!btn || !menu) return
  const rect = btn.getBoundingClientRect()
  const menuRect = menu.getBoundingClientRect()
  const left = rect.left
  let top = rect.top - menuRect.height - 8
  if (top < 8) top = rect.bottom + 8
  userMenuStyle.value = { left: `${left}px`, top: `${top}px` }
}

function onClickOutside(e: MouseEvent) {
  const target = e.target as Node
  if (
    userMenuVisible.value &&
    userBtnRef.value &&
    !userBtnRef.value.contains(target) &&
    userMenuRef.value &&
    !userMenuRef.value.contains(target)
  ) {
    userMenuVisible.value = false
  }
  if (
    notifyVisible.value &&
    notifyBtnRef.value &&
    !notifyBtnRef.value.contains(target) &&
    notifyMenuRef.value &&
    !notifyMenuRef.value.contains(target)
  ) {
    notifyVisible.value = false
  }
}

function onResize() {
  userMenuVisible.value = false
  notifyVisible.value = false
  checkMobile()
}

onMounted(() => {
  checkMobile()
  loadNotifications()
  loadProfile()
  document.addEventListener('click', onClickOutside)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
  background: var(--xy-bg-page);
}

/* 侧边栏 - 玻璃拟态 + 深空氛围 */
.sidebar {
  width: var(--xy-sidebar-w, 240px);
  min-width: var(--xy-sidebar-w, 240px);
  background:
    linear-gradient(180deg, rgba(19, 17, 28, 0.98) 0%, rgba(14, 12, 20, 0.98) 100%),
    var(--xy-bg-canvas);
  border-right: 1px solid var(--xy-border-1);
  display: flex;
  flex-direction: column;
  transition: width var(--xy-dur-md) ease, min-width var(--xy-dur-md) ease;
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
}

.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(circle at 30% 20%, rgba(139, 126, 200, 0.06) 0%, transparent 50%),
    radial-gradient(circle at 70% 80%, rgba(212, 168, 83, 0.04) 0%, transparent 45%);
}

.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
}

.sidebar.collapsed .sidebar-text {
  display: none;
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: var(--xy-overlay);
  backdrop-filter: blur(4px);
  z-index: var(--xy-z-drawer-backdrop, 300);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--xy-border-1);
  min-height: 64px;
  flex-shrink: 0;
  position: relative;
}

.brand-icon {
  flex-shrink: 0;
  filter: drop-shadow(0 0 12px rgba(139, 126, 200, 0.35));
  transition: transform var(--xy-dur-md) var(--xy-ease-spring);
}

.sidebar-brand:hover .brand-icon {
  transform: rotate(15deg) scale(1.05);
}

.brand-text {
  font-family: var(--xy-font-display);
  font-weight: 600;
  font-size: 19px;
  letter-spacing: 0.06em;
  white-space: nowrap;
  color: var(--xy-text-1);
  background: linear-gradient(135deg, var(--xy-text-1) 0%, var(--xy-brand-starlight) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 统计区 - 胶囊卡片 */
.sidebar-stats {
  padding: 16px 18px;
  flex-shrink: 0;
}

.stats-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg, 10px);
}

.stat-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.stat-mini-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--xy-text-1);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.stat-mini-label {
  font-size: 10px;
  color: var(--xy-text-4);
  white-space: nowrap;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.stat-mini-divider {
  width: 1px;
  height: 28px;
  background: var(--xy-border-1);
}

/* 导航 - 悬浮胶囊 + 激活光效 */
.sidebar-nav {
  flex: 1;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  color: var(--xy-text-3);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--xy-radius-md, 8px);
  transition: all var(--xy-dur-sm);
  border: 1px solid transparent;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--xy-accent), var(--xy-brand-500));
  opacity: 0;
  transition: opacity var(--xy-dur-sm);
  border-radius: 0 2px 2px 0;
}

.nav-item:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-1);
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(212, 168, 83, 0.12) 0%, rgba(139, 126, 200, 0.08) 100%);
  color: var(--xy-text-1);
  border-color: rgba(212, 168, 83, 0.2);
  box-shadow: inset 0 0 20px rgba(212, 168, 83, 0.05);
}

.nav-item.active::before {
  opacity: 1;
}

.nav-item.active .nav-icon {
  color: var(--xy-accent);
}

.nav-icon {
  flex-shrink: 0;
  width: 17px;
  height: 17px;
  transition: color var(--xy-dur-sm);
}

.nav-icon :deep(path),
.nav-icon :deep(g) {
  stroke-width: 1.7;
}

/* 折叠/窄边栏：导航图标居中 */
.sidebar.collapsed .nav-item,
.sidebar.collapsed .bottom-link {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
  border-left-color: transparent;
}

.sidebar.collapsed .nav-item::before {
  display: none;
}

.sidebar.collapsed .user-area {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.sidebar.collapsed .user-arrow {
  display: none;
}

.icon-12 {
  width: 12px;
  height: 12px;
}

.icon-14 {
  width: 14px;
  height: 14px;
}

.icon-16 {
  width: 16px;
  height: 16px;
}

.icon-18 {
  width: 18px;
  height: 18px;
}

/* 底部 */
.sidebar-bottom {
  padding: 12px 14px;
  border-top: 1px solid var(--xy-border-1);
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.bottom-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  color: var(--xy-text-4);
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--xy-radius-sm, 5px);
  transition: all var(--xy-dur-sm);
}

.bottom-link:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

/* 用户区 - 悬浮卡片 */
.user-area {
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: var(--xy-radius-md, 8px);
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.user-area:hover {
  background: var(--xy-surface-hover);
  border-color: var(--xy-border-2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: var(--xy-radius-full, 9999px);
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  border: 1px solid rgba(212, 168, 83, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--xy-brand-starlight);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.25);
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-tier {
  font-size: 11px;
  color: var(--xy-text-4);
}

.user-arrow {
  color: var(--xy-text-4);
  flex-shrink: 0;
  transition: transform var(--xy-dur-sm);
}

.app-layout.menu-open .user-arrow {
  transform: rotate(180deg);
}

/* 用户菜单 - 玻璃面板 */
.user-menu {
  position: fixed;
  width: 230px;
  background: rgba(24, 22, 34, 0.96);
  border: 1px solid var(--xy-border-2);
  border-radius: var(--xy-radius-lg, 10px);
  box-shadow: var(--xy-shadow-modal);
  padding: 8px;
  z-index: var(--xy-z-popover, 500);
  animation: menu-pop var(--xy-dur-sm) var(--xy-ease-spring);
  backdrop-filter: blur(16px);
}

@keyframes menu-pop {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(-6px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
}

.menu-avatar {
  width: 38px;
  height: 38px;
  border-radius: var(--xy-radius-full, 9999px);
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  border: 1px solid rgba(212, 168, 83, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--xy-brand-starlight);
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 2px 10px rgba(124, 108, 191, 0.25);
}

.menu-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.menu-email {
  font-size: 11px;
  color: var(--xy-text-4);
}

.menu-divider {
  height: 1px;
  background: var(--xy-border-1);
  margin: 6px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--xy-radius-sm, 5px);
  font-size: 13px;
  color: var(--xy-text-2);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.menu-item:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.menu-item-wrap {
  position: relative;
}

.theme-switcher-below {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
}

.theme-switcher-below :deep(.ts-btn) {
  display: none;
}

.menu-kbd {
  margin-left: auto;
  font-size: 10px;
  color: var(--xy-text-4);
  background: var(--xy-surface-2);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--xy-font-mono, monospace);
}

.menu-danger {
  color: var(--xy-danger);
}

.menu-danger:hover {
  background: var(--xy-danger-bg);
}

/* 主内容区 */
.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.topbar {
  height: var(--xy-topbar-h, 56px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(17, 15, 24, 0.85);
  border-bottom: 1px solid var(--xy-border-1);
  flex-shrink: 0;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sidebar-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
  border-radius: var(--xy-radius-sm, 5px);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.sidebar-toggle:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-2);
}

.module-title {
  font-family: var(--xy-font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.03em;
  margin: 0;
  color: var(--xy-text-1);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.topbar-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
  border-radius: var(--xy-radius-sm, 5px);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.topbar-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-2);
}

.notify-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 15px;
  height: 15px;
  padding: 0 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--xy-accent), #e8a85a);
  color: #1a1525;
  font-size: 9px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 2px 6px rgba(212, 168, 83, 0.35);
}

.ai-status {
  font-size: 11px;
  font-weight: 500;
  color: var(--xy-text-3);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
  padding: 5px 12px;
  border-radius: var(--xy-radius-full, 9999px);
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-success);
  box-shadow: 0 0 8px var(--xy-success);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

/* 通知下拉 - 玻璃面板 */
.notify-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 340px;
  max-width: calc(100vw - 32px);
  max-height: 420px;
  background: rgba(24, 22, 34, 0.96);
  border: 1px solid var(--xy-border-2);
  border-radius: var(--xy-radius-lg, 10px);
  box-shadow: var(--xy-shadow-modal);
  z-index: var(--xy-z-popover, 500);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: menu-pop var(--xy-dur-sm) var(--xy-ease-spring);
  backdrop-filter: blur(16px);
}

.notify-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--xy-border-1);
  flex-shrink: 0;
}

.notify-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.notify-actions {
  display: flex;
  gap: 12px;
}

.notify-action {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--xy-text-4);
  cursor: pointer;
  transition: color var(--xy-dur-sm);
}

.notify-action:hover {
  color: var(--xy-brand-starlight);
}

.notify-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.notify-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-radius: var(--xy-radius-md, 8px);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
  border: 1px solid transparent;
}

.notify-item:hover {
  background: var(--xy-surface-hover);
  border-color: var(--xy-border-1);
}

.notify-item.unread {
  background: color-mix(in srgb, var(--xy-brand-500) 6%, transparent);
  border-color: rgba(139, 126, 200, 0.15);
}

.notify-item.unread:hover {
  background: color-mix(in srgb, var(--xy-brand-500) 10%, transparent);
}

.notify-item-main {
  flex: 1;
  min-width: 0;
}

.notify-item-title {
  margin: 0 0 5px;
  font-size: 13px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.notify-item-msg {
  margin: 0;
  font-size: 12px;
  color: var(--xy-text-3);
  line-height: 1.5;
}

.notify-item-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--xy-text-4);
  white-space: nowrap;
}

.notify-empty {
  padding: 40px 0;
  text-align: center;
  font-size: 13px;
  color: var(--xy-text-3);
}

.content-area {
  flex: 1;
  overflow-y: auto;
  background: var(--xy-bg-page);
  position: relative;
}

/* 帮助中心 */
.help-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.help-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.help-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin-bottom: 2px;
}

.help-icon {
  width: 15px;
  height: 15px;
  color: var(--xy-brand-starlight);
}

.help-shortcuts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.help-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--xy-text-2);
}

.help-label {
  flex: 1;
  min-width: 0;
}

.help-kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 5px;
  background: var(--xy-surface-2);
  border: 1px solid var(--xy-border-1);
  font-size: 11px;
  color: var(--xy-text-2);
  font-family: var(--xy-font-mono, monospace);
}

.help-text {
  margin: 0;
  font-size: 13px;
  color: var(--xy-text-2);
  line-height: 1.6;
}

/* 个人资料 */
.profile-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.profile-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--xy-border-1);
}

.profile-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  border: 2px solid rgba(212, 168, 83, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--xy-brand-starlight);
  font-size: 24px;
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(124, 108, 191, 0.3);
}

.profile-avatar-hint {
  margin: 0;
  font-size: 12px;
  color: var(--xy-text-4);
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.profile-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--xy-text-2);
}

.profile-input,
.profile-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-1);
  font-size: 13px;
  font-family: var(--xy-font-sans);
  outline: none;
  transition: all var(--xy-dur-sm);
}

.profile-input:hover,
.profile-textarea:hover {
  border-color: var(--xy-border-2);
  background: var(--xy-surface-hover);
}

.profile-input:focus,
.profile-textarea:focus {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
  background: var(--xy-surface-hover);
}

.profile-input::placeholder,
.profile-textarea::placeholder {
  color: var(--xy-text-4);
}

.profile-textarea {
  resize: vertical;
  line-height: 1.5;
}

/* 响应式 */
@media (max-width: 1024px) {
  .sidebar {
    width: 60px;
    min-width: 60px;
  }
  .sidebar-text {
    display: none;
  }
  .sidebar-stats {
    display: none;
  }
  .sidebar-brand {
    justify-content: center;
    padding: 18px 0;
  }
  .nav-item,
  .bottom-link {
    justify-content: center;
    padding-left: 0;
    padding-right: 0;
    border-left-color: transparent;
  }
  .nav-item::before {
    display: none;
  }
  .user-area {
    justify-content: center;
    padding-left: 0;
    padding-right: 0;
  }
  .user-arrow {
    display: none;
  }
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: var(--xy-z-drawer, 310);
    transform: translateX(0);
    transition: transform var(--xy-dur-md) ease;
  }
  .sidebar.collapsed {
    transform: translateX(-100%);
  }
  .user-menu {
    left: 8px !important;
    right: 8px;
    width: auto;
  }
  .topbar {
    padding: 0 16px;
  }
}
</style>