<template>
  <Teleport to="body">
    <Transition name="xy-drawer-fade">
      <div v-if="innerVisible" class="xy-drawer-mask" @click="handleMaskClick"></div>
    </Transition>
    <Transition :name="placement === 'left' ? 'xy-drawer-slide-left' : 'xy-drawer-slide-right'">
      <div
        v-if="innerVisible"
        class="xy-drawer"
        :class="`xy-drawer-${placement}`"
        :style="{ width: width }"
        role="dialog"
        aria-modal="true"
      >
        <div class="xy-drawer-header">
          <slot name="header">
            <span class="xy-drawer-title">{{ title }}</span>
          </slot>
          <button class="xy-drawer-close" aria-label="关闭" @click="handleClose">
            <X class="xy-drawer-close-icon" />
          </button>
        </div>
        <div class="xy-drawer-body">
          <slot />
        </div>
        <div v-if="$slots.footer" class="xy-drawer-footer">
          <slot name="footer" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from '@vicons/tabler'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    placement?: 'left' | 'right'
    width?: string
    title?: string
  }>(),
  {
    placement: 'right',
    width: '320px',
    title: '',
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  close: []
}>()

const innerVisible = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    innerVisible.value = val
  },
  { immediate: true }
)

function handleClose() {
  innerVisible.value = false
  emit('update:modelValue', false)
  emit('close')
}

function handleMaskClick() {
  handleClose()
}
</script>

<style scoped>
.xy-drawer-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--xy-overlay);
  z-index: var(--xy-z-drawer-backdrop);
}

.xy-drawer {
  position: fixed;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  z-index: var(--xy-z-drawer);
  box-shadow: var(--xy-shadow-lg);
}

.xy-drawer-left {
  left: 0;
  border-right: var(--xy-border-w-1) solid var(--xy-border-1);
}

.xy-drawer-right {
  right: 0;
  border-left: var(--xy-border-w-1) solid var(--xy-border-1);
}

.xy-drawer-header {
  height: var(--xy-panel-header-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-4);
  border-bottom: var(--xy-border-w-1) solid var(--xy-divider);
}

.xy-drawer-title {
  font-size: var(--xy-fs-md);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
}

.xy-drawer-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--xy-radius-md);
  background: transparent;
  border: none;
  color: var(--xy-text-3);
  cursor: pointer;
  transition:
    color var(--xy-dur-sm) var(--xy-ease-standard),
    background var(--xy-dur-sm) var(--xy-ease-standard);
}

.xy-drawer-close:hover {
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
}

.xy-drawer-close-icon {
  width: 16px;
  height: 16px;
}

.xy-drawer-body {
  flex: 1;
  overflow-y: auto;
}

.xy-drawer-footer {
  flex-shrink: 0;
  padding: var(--xy-space-3) var(--xy-space-4);
  border-top: var(--xy-border-w-1) solid var(--xy-divider);
}

.xy-drawer-fade-enter-active,
.xy-drawer-fade-leave-active {
  transition: opacity var(--xy-dur-md) var(--xy-ease-standard);
}

.xy-drawer-fade-enter-from,
.xy-drawer-fade-leave-to {
  opacity: 0;
}

.xy-drawer-slide-left-enter-active,
.xy-drawer-slide-left-leave-active,
.xy-drawer-slide-right-enter-active,
.xy-drawer-slide-right-leave-active {
  transition: transform var(--xy-dur-lg) var(--xy-ease-standard);
}

.xy-drawer-slide-left-enter-from,
.xy-drawer-slide-left-leave-to {
  transform: translateX(-100%);
}

.xy-drawer-slide-right-enter-from,
.xy-drawer-slide-right-leave-to {
  transform: translateX(100%);
}
</style>
