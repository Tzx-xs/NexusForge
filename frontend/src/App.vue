<template>
  <n-config-provider :theme="themeStore.appTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-loading-bar-provider>
            <router-view/>
            <div class="xy-noise-overlay" />

            <!-- B13 启动骨架屏 -->
            <Transition name="xy-boot-fade">
              <div v-if="appBooting" class="app-boot-skeleton" aria-hidden="true">
                <div class="boot-shell">
                  <div class="boot-sidebar">
                    <div class="boot-logo shimmer"></div>
                    <div class="boot-nav shimmer"></div>
                    <div class="boot-nav shimmer"></div>
                    <div class="boot-nav shimmer"></div>
                    <div class="boot-nav shimmer"></div>
                  </div>
                  <div class="boot-main">
                    <div class="boot-topbar shimmer"></div>
                    <div class="boot-card shimmer"></div>
                    <div class="boot-card shimmer"></div>
                    <div class="boot-card shimmer"></div>
                  </div>
                </div>
              </div>
            </Transition>
          </n-loading-bar-provider>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLoadingBarProvider,
  type GlobalThemeOverrides,
} from 'naive-ui'
import { computed, onMounted, onUnmounted, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
themeStore.init()

// B13 启动骨架屏：在首屏路由就绪前显示 App 外壳骨架，消除白屏/闪白观感
const router = useRouter()
const appBooting = ref(true)
router
  .isReady()
  .then(() => requestAnimationFrame(() => (appBooting.value = false)))
// 安全兜底：无论如何 2s 后必定隐藏，避免异常情况下骨架常驻
window.setTimeout(() => (appBooting.value = false), 2000)

// 移动端检测
const isMobile = ref(false)
provide('isMobile', isMobile)

onMounted(() => {
  // B6 修复：统一移动端断点为 768px，与 AppLayout / main.css 保持一致（消除 767/768 偏差）
  const mq = window.matchMedia('(max-width: 768px)')
  isMobile.value = mq.matches
  const handler = (e: MediaQueryListEvent) => { isMobile.value = e.matches }
  mq.addEventListener('change', handler)
  onUnmounted(() => mq.removeEventListener('change', handler))
})

// 动态主题覆盖：根据当前主题切换 naive-ui 主色
// 使用 shallowRef 避免深层响应，并在 effectiveMode 未就绪时给安全默认值
const themeOverrides = computed<GlobalThemeOverrides>(() => {
  const mode = themeStore.effectiveMode ?? 'abyss'
  const isLight = mode === 'light'
  return {
    common: {
      primaryColor: isLight ? '#6366f1' : '#7c6cbf',
      primaryColorHover: isLight ? '#818cf8' : '#9585d4',
      primaryColorPressed: isLight ? '#4f46e5' : '#5846a8',
      primaryColorSuppl: isLight ? '#818cf8' : '#9585d4',
      borderRadius: '8px',
    },
  }
})

// Sprint 6.1: Ctrl+Shift+L 循环切换主题(light→dark→abyss)
function handleKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.shiftKey && (e.key === 'L' || e.key === 'l')) {
    e.preventDefault()
    themeStore.toggleMode()
  }
}
onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  themeStore.destroy()
})
</script>

<style>
/* 使用系统原生字体替代 Google Fonts（SEC-H2：离线可用 + 隐私保护）。
   原 Google Fonts 映射:
   Playfair Display → Georgia (serif)
   Inter           → system-ui (sans-serif)
   Noto Serif SC   → "Songti SC" / SimSun (中文字体)
   如需自定义字体，将 .woff2 文件放到 src/assets/fonts/ 并用 @font-face 引用。
*/
:root {
  --xy-font-display: Georgia, "Times New Roman", "Noto Serif SC", "Songti SC", SimSun, serif;
  --xy-font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  --xy-font-mono: ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, "DejaVu Sans Mono", monospace;
}

/* ========== B13 启动骨架屏 ========== */
.app-boot-skeleton {
  position: fixed;
  inset: 0;
  z-index: var(--xy-z-loading);
  background: var(--xy-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.boot-shell {
  width: 100%;
  max-width: 1100px;
  height: 78vh;
  display: flex;
  gap: 16px;
}

.boot-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.boot-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.boot-topbar {
  height: 52px;
  border-radius: var(--xy-radius-lg);
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
}

.boot-card {
  flex: 1;
  border-radius: var(--xy-radius-lg);
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
}

.boot-logo {
  width: 120px;
  height: 26px;
  border-radius: var(--xy-radius-sm);
}

.boot-nav {
  height: 36px;
  border-radius: var(--xy-radius-sm);
}

.shimmer {
  background: linear-gradient(
    90deg,
    var(--xy-surface-2) 25%,
    var(--xy-surface-3) 37%,
    var(--xy-surface-2) 63%
  );
  background-size: 400% 100%;
  animation: xy-shimmer 1.5s ease-in-out infinite;
}

.xy-boot-fade-leave-active {
  transition: opacity var(--xy-dur-md) var(--xy-ease-standard);
}

.xy-boot-fade-leave-to {
  opacity: 0;
}
</style>
