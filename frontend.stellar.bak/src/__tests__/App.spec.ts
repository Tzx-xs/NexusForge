import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// 使用 vi.hoisted 避免 mock 工厂引用未初始化变量
const { toggleModeSpy } = vi.hoisted(() => ({
  toggleModeSpy: vi.fn(),
}))

vi.mock('@/stores/theme', () => ({
  useThemeStore: () => ({
    init: vi.fn(),
    appTheme: { name: 'mock-theme' },
    toggleMode: toggleModeSpy,
  }),
}))

vi.mock('naive-ui', () => ({
  NConfigProvider: { template: '<div><slot /></div>' },
  NMessageProvider: { template: '<div><slot /></div>' },
  NDialogProvider: { template: '<div><slot /></div>' },
  NNotificationProvider: { template: '<div><slot /></div>' },
  NLoadingBarProvider: { template: '<div><slot /></div>' },
}))

import App from '@/App.vue'

describe('App.vue Ctrl+Shift+L 主题快捷键', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  function mountApp() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
    return mount(App, {
      global: {
        plugins: [
          createPinia(),
          router,
        ],
      },
    })
  }

  it('Ctrl+Shift+L 触发 themeStore.toggleMode', async () => {
    mountApp()
    const event = new KeyboardEvent('keydown', {
      key: 'L',
      ctrlKey: true,
      shiftKey: true,
      bubbles: true,
    })
    window.dispatchEvent(event)
    expect(toggleModeSpy).toHaveBeenCalledTimes(1)
  })
})
