<template>
  <AppLayout :active-module="activeModule" @switch-module="switchModule">
    <Transition name="module-fade" mode="out-in">
      <component :is="currentComponent" :key="activeModule"/>
    </Transition>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, defineAsyncComponent, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const NewNovel = defineAsyncComponent(() => import('@/views/dashboard/NewNovel.vue'))
const MyNovels = defineAsyncComponent(() => import('@/views/dashboard/MyNovels.vue'))
const ContentReview = defineAsyncComponent(() => import('@/views/dashboard/ContentReview.vue'))
const WorldviewManager = defineAsyncComponent(() => import('@/views/dashboard/WorldviewManager.vue'))

const route = useRoute()
const router = useRouter()

const VALID_MODULES = ['new-novel', 'my-novels', 'content-review', 'worldview'] as const

type ModuleKey = (typeof VALID_MODULES)[number]
const DEFAULT_MODULE: ModuleKey = 'my-novels'

function isValidModule(value: unknown): value is ModuleKey {
  return typeof value === 'string' && (VALID_MODULES as readonly string[]).includes(value)
}

function resolveModule(value: unknown): ModuleKey {
  return isValidModule(value) ? value : DEFAULT_MODULE
}

const activeModule = ref<ModuleKey>(resolveModule(route.query.module))

const componentMap: Record<ModuleKey, Component> = {
  'new-novel': NewNovel,
  'my-novels': MyNovels,
  'content-review': ContentReview,
  'worldview': WorldviewManager,
}

const currentComponent = computed(() => componentMap[activeModule.value] ?? NewNovel)

// 通过 afterEach 将 URL query 同步到本地状态，避免双向 watch 循环
const unsubscribe = router.afterEach((to) => {
  activeModule.value = resolveModule(to.query.module)
})
onBeforeUnmount(unsubscribe)

function switchModule(module: string) {
  const target = resolveModule(module)
  if (route.query.module !== target) {
    router.replace({ query: { ...route.query, module: target } })
  } else {
    activeModule.value = target
  }
}
</script>
