import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useThemeStore } from '@/stores/theme'

describe('themeStore toggleMode', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // mock matchMedia 默认返回 light(prefers-color-scheme: light)
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
    }))
    // mock localStorage 避免 getInitialMode 读取真实存储
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    })
  })

  it('toggleMode 在 light→dark→abyss 间循环', () => {
    const store = useThemeStore()
    store.setMode('light')

    store.toggleMode()
    expect(store.mode).toBe('dark')

    store.toggleMode()
    expect(store.mode).toBe('abyss')

    store.toggleMode()
    expect(store.mode).toBe('light')
  })

  it('toggleMode 从 system 切换到 light(解析 system 后切换为实际主题)', () => {
    const store = useThemeStore()
    store.setMode('system')
    // matchMedia 返回 light,故 effectiveMode = 'light'
    store.toggleMode()
    expect(store.mode).toBe('light')
  })
})
