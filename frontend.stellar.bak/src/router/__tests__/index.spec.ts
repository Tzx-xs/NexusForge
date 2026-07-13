import { describe, it, expect, beforeEach } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import router from '@/router'

describe('Router', () => {
  beforeEach(() => {
    localStorage.setItem('xy-last-novel', '1')
  })

  it('should redirect /bible to workspace writing', async () => {
    const testRouter = createRouter({
      history: createMemoryHistory(),
      routes: router.options.routes,
    })

    await testRouter.push('/bible')
    await testRouter.isReady()

    const route = testRouter.currentRoute.value
    expect(route.path).toBe('/workspace/1/writing/1')
  })

  it('should redirect /outline to workspace writing', async () => {
    const testRouter = createRouter({
      history: createMemoryHistory(),
      routes: router.options.routes,
    })

    await testRouter.push('/outline')
    await testRouter.isReady()

    const route = testRouter.currentRoute.value
    expect(route.path).toBe('/workspace/1/writing/1')
  })

  it('should have /characters route', async () => {
    const testRouter = createRouter({
      history: createMemoryHistory(),
      routes: router.options.routes,
    })

    await testRouter.push('/characters')
    await testRouter.isReady()

    const route = testRouter.currentRoute.value
    expect(route.name).toBe('characters')
  })

  it('should have /review route', async () => {
    const testRouter = createRouter({
      history: createMemoryHistory(),
      routes: router.options.routes,
    })

    await testRouter.push('/review')
    await testRouter.isReady()

    const route = testRouter.currentRoute.value
    expect(route.name).toBe('review')
  })

  it('should have /settings route', async () => {
    const testRouter = createRouter({
      history: createMemoryHistory(),
      routes: router.options.routes,
    })

    await testRouter.push('/settings')
    await testRouter.isReady()

    const route = testRouter.currentRoute.value
    expect(route.name).toBe('settings')
  })
})
