<template>
  <div class="not-found-page">
    <div class="not-found-card">
      <div class="error-code">404</div>
      <div class="error-title">页面不存在</div>
      <div class="error-desc">您访问的页面可能已被移除或地址有误</div>
      <n-button type="primary" @click="router.push('/')">返回首页</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'

const router = useRouter()
</script>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--xy-bg-page);
  padding: var(--xy-space-6);
}

.not-found-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-4);
  padding: var(--xy-space-16) var(--xy-space-12);
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-2);
  border-radius: var(--xy-radius-2xl);
  box-shadow: var(--xy-shadow-lg);
  text-align: center;
}

.error-code {
  font-family: var(--xy-font-display);
  font-size: 6rem;
  font-weight: var(--xy-fw-bold);
  line-height: var(--xy-lh-display);
  letter-spacing: var(--xy-tracking-tight);
  color: var(--xy-brand-500);
  text-shadow: 0 0 32px rgba(124, 108, 191, 0.35);
}

.error-title {
  font-family: var(--xy-font-sans);
  font-size: var(--xy-fs-2xl);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
  letter-spacing: var(--xy-tracking-wide);
}

.error-desc {
  font-family: var(--xy-font-sans);
  font-size: var(--xy-fs-md);
  color: var(--xy-text-3);
  line-height: var(--xy-lh-normal);
}

.not-found-card :deep(.n-button--primary-type) {
  background-color: var(--xy-brand-500);
  border-color: var(--xy-brand-500);
  margin-top: var(--xy-space-2);
}

.not-found-card :deep(.n-button--primary-type:hover) {
  background-color: var(--xy-brand-600);
  border-color: var(--xy-brand-600);
}
</style>
