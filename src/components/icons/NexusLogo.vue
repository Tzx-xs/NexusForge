<template>
  <div class="nexus-logo" :class="[`size-${size}`, { 'is-rotating': isRotating }]">
    <svg
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
      class="logo-svg"
    >
      <defs>
        <linearGradient id="nexus-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="var(--nexus-gradient-start, #06b6d4)" />
          <stop offset="50%" stop-color="var(--nexus-gradient-mid, #3b82f6)" />
          <stop offset="100%" stop-color="var(--nexus-gradient-end, #8b5cf6)" />
        </linearGradient>
      </defs>

      <!-- 等距立方体 - 三个可见面 -->
      <!-- 顶面 -->
      <path
        class="face face-top"
        d="M50 20 L80 37.5 L50 55 L20 37.5 Z"
        fill="url(#nexus-gradient)"
        opacity="0.9"
      />
      <!-- 左面 -->
      <path
        class="face face-left"
        d="M20 37.5 L50 55 L50 85 L20 67.5 Z"
        fill="url(#nexus-gradient)"
        opacity="0.7"
      />
      <!-- 右面 -->
      <path
        class="face face-right"
        d="M80 37.5 L50 55 L50 85 L80 67.5 Z"
        fill="url(#nexus-gradient)"
        opacity="0.5"
      />

      <!-- N 字母 -->
      <text
        x="50"
        y="58"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="white"
        font-size="24"
        font-weight="700"
        font-family="Inter, system-ui, sans-serif"
        class="logo-letter"
      >
        N
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: 'sm' | 'md' | 'lg' | 'xl'; isRotating?: boolean }>(), {
  size: 'md',
  isRotating: false,
})
</script>

<style scoped>
.nexus-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-svg {
  width: 100%;
  height: 100%;
}

/* 尺寸 */
.size-sm { width: 24px; height: 24px; }
.size-md { width: 32px; height: 32px; }
.size-lg { width: 48px; height: 48px; }
.size-xl { width: 64px; height: 64px; }

/* 悬停旋转动画 */
.is-rotating .logo-svg {
  animation: logoRotate 2s ease-in-out infinite;
}

@keyframes logoRotate {
  0%, 100% { transform: rotateY(0deg); }
  50% { transform: rotateY(15deg); }
}

/* 深色模式变量 */
:root {
  --nexus-gradient-start: #06b6d4;
  --nexus-gradient-mid: #3b82f6;
  --nexus-gradient-end: #8b5cf6;
}
</style>
