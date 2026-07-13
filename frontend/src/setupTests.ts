import { beforeEach, vi } from 'vitest'

const storage: Record<string, string> = {}

const localStorageMock = {
  getItem: (key: string) => storage[key] ?? null,
  setItem: (key: string, value: string) => {
    storage[key] = String(value)
  },
  removeItem: (key: string) => {
    delete storage[key]
  },
  clear: () => {
    Object.keys(storage).forEach((key) => delete storage[key])
  },
}

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

class MatchMediaMock {
  matches = false
  media = ''
  onchange = null
  addListener = vi.fn()
  removeListener = vi.fn()
  addEventListener = vi.fn()
  removeEventListener = vi.fn()
  dispatchEvent = vi.fn()
  constructor(query: string) {
    this.media = query
  }
}

Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: (query: string) => new MatchMediaMock(query),
})

class ResizeObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  constructor() {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
})

beforeEach(() => {
  localStorageMock.clear()
})
