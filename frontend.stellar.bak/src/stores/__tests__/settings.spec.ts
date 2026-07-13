import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSettingsStore } from '../settings'

describe('Settings Store - localStorage Validation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('should fall back gracefully when localStorage contains invalid JSON', async () => {
    localStorage.setItem('xy-settings', '{invalid json')

    vi.mock('@/api/settings', () => ({
      getSettings: vi.fn().mockRejectedValue(new Error('Network error')),
      updateSettings: vi.fn(),
      resetSettings: vi.fn(),
    }))

    const store = useSettingsStore()

    await store.fetchSettings()

    expect(store.settings).toBeDefined()
    expect(typeof store.settings).toBe('object')
  })

  it('should validate localStorage data has correct shape (string values only)', async () => {
    localStorage.setItem(
      'xy-settings',
      JSON.stringify({
        theme: 'dark',
        someNumber: 123,
        nested: { key: 'value' },
      })
    )

    vi.mock('@/api/settings', () => ({
      getSettings: vi.fn().mockRejectedValue(new Error('Network error')),
      updateSettings: vi.fn(),
      resetSettings: vi.fn(),
    }))

    const store = useSettingsStore()

    await store.fetchSettings()

    Object.values(store.settings).forEach((value) => {
      expect(typeof value).toBe('string')
    })
  })
})
